"""
Historical Fire Data Import System
Imports NASA FIRMS CSV files into GEOWISE database with metadata generation.
"""

import asyncio
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

import sys
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.database import init_db, close_db, get_db
from app.models import FireDetection
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FireImporter:
    """Manages import of historical fire data from CSV files."""
    
    def __init__(self, data_root: Path):
        self.data_root = data_root
        self.stats = {
            "files_processed": 0,
            "total_imported": 0,
            "total_errors": 0,
            "countries": {}
        }
    
    def discover_files(self, country: str = None) -> List[Dict]:
        """
        Discover CSV files to import.
        
        FIXED: Robust filename parsing that handles:
        - .csv extension properly
        - Case-insensitive folder names
        - Invalid filenames gracefully
        """
        historical_dir = self.data_root / "fires" / "historical"
        
        if not historical_dir.exists():
            logger.error(f"Historical data directory not found: {historical_dir}")
            return []
        
        files = []
        pattern = f"{country}/" if country else "*/"
        
        for csv_file in historical_dir.glob(f"{pattern}*.csv"):
            # Remove .csv extension using .stem
            filename_no_ext = csv_file.stem
            
            # Split by underscore
            parts = filename_no_ext.split('_')
            
            logger.debug(f"Processing: {csv_file.name}")
            logger.debug(f"  Stem: {filename_no_ext}")
            logger.debug(f"  Parts: {parts}")
            
            # Expected format: {country}_fires_viirs_{satellite}_{year}
            # Example: pak_fires_viirs_suomi_2020
            if len(parts) >= 5:
                try:
                    # Extract year - remove any remaining .csv just in case
                    year_part = parts[4].replace('.csv', '').strip()
                    
                    file_info = {
                        "path": csv_file,
                        "country": parts[0].upper(),
                        "satellite": parts[3],
                        "year": int(year_part)
                    }
                    files.append(file_info)
                    logger.debug(f"  ✅ Parsed successfully: {file_info}")
                    
                except (ValueError, IndexError) as e:
                    logger.warning(f"  ❌ Failed to parse {csv_file.name}: {e}")
                    logger.warning(f"     Expected format: {{country}}_fires_viirs_{{satellite}}_{{year}}.csv")
                    continue
            else:
                logger.warning(f"  ⚠️  Invalid filename format: {csv_file.name}")
                logger.warning(f"     Expected 5 parts (e.g., pak_fires_viirs_suomi_2020), got {len(parts)}")
        
        return sorted(files, key=lambda x: (x['country'], x['year']))
    
    async def import_csv(self, file_info: Dict, batch_size: int = 1000) -> Dict:
        """
        Import a single CSV file.
        
        FEATURES:
        - Batch processing (1000 records at a time)
        - Progress tracking
        - Error logging
        - Automatic date conversion
        """
        csv_path = file_info['path']
        country = file_info['country']
        year = file_info['year']
        satellite = file_info['satellite']
        
        logger.info(f"Importing: {csv_path.name}")
        
        try:
            # Read CSV
            logger.info(f"  📖 Reading CSV file...")
            df = pd.read_csv(csv_path)
            
            # Convert date format (handles MM/DD/YYYY format from NASA)
            logger.info(f"  📅 Converting date format...")
            df['acq_date'] = pd.to_datetime(df['acq_date'])
            
            total = len(df)
            imported = 0
            errors = 0
            
            logger.info(f"  📊 Records to import: {total:,}")
            
            async for session in get_db():
                for idx, row in df.iterrows():
                    try:
                        fire = FireDetection(
                            latitude=float(row['latitude']),
                            longitude=float(row['longitude']),
                            country=country,
                            brightness=float(row['brightness']),
                            frp=float(row['frp']) if pd.notna(row['frp']) else None,
                            confidence=str(row['confidence']).lower() if pd.notna(row['confidence']) else None,
                            acq_date=row['acq_date'],
                            acq_time=str(row['acq_time']).zfill(4) if 'acq_time' in row else None,
                            satellite=satellite.upper(),
                            instrument='VIIRS',
                            daynight=str(row['daynight']) if 'daynight' in row else None,
                            scan=float(row['scan']) if 'scan' in row and pd.notna(row['scan']) else None,
                            track=float(row['track']) if 'track' in row and pd.notna(row['track']) else None
                        )
                        
                        session.add(fire)
                        imported += 1
                        
                        # Commit in batches
                        if imported % batch_size == 0:
                            await session.commit()
                            progress = (imported / total) * 100
                            logger.info(f"  💾 Progress: {imported:,}/{total:,} ({progress:.1f}%)")
                    
                    except Exception as e:
                        errors += 1
                        if errors <= 3:  # Log first 3 errors only
                            logger.error(f"  ❌ Error at row {idx}: {e}")
                
                # Final commit
                await session.commit()
            
            logger.info(f"  ✅ Import complete: {imported:,} imported, {errors:,} errors")
            
            return {
                "file": csv_path.name,
                "country": country,
                "year": year,
                "satellite": satellite,
                "imported": imported,
                "errors": errors,
                "total": total
            }
        
        except Exception as e:
            logger.error(f"  ❌ Failed to import {csv_path.name}: {e}")
            import traceback
            traceback.print_exc()
            return {
                "file": csv_path.name,
                "country": country,
                "year": year,
                "imported": 0,
                "errors": total if 'total' in locals() else 0,
                "error": str(e)
            }
    
    async def generate_metadata(self, country: str):
        """
        Generate metadata JSON for country.
        
        Creates a summary file in data/fires/metadata/{country}.json
        """
        metadata_dir = self.data_root / "fires" / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            async for session in get_db():
                from sqlalchemy import text
                
                # Get summary stats using raw SQL
                result = await session.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total_fires,
                            MIN(acq_date) as start_date,
                            MAX(acq_date) as end_date,
                            AVG(frp) as avg_frp,
                            COUNT(DISTINCT satellite) as satellites
                        FROM fire_detections
                        WHERE country = :country
                    """),
                    {"country": country}
                )
                stats = result.fetchone()
                
                if not stats or stats[0] == 0:
                    logger.warning(f"No data found for {country}")
                    return
                
                # Get years available
                years_result = await session.execute(
                    text("""
                        SELECT DISTINCT strftime('%Y', acq_date) as year
                        FROM fire_detections
                        WHERE country = :country
                        ORDER BY year
                    """),
                    {"country": country}
                )
                years = [int(row[0]) for row in years_result.fetchall()]
                
                metadata = {
                    "country": country,
                    "country_name": self._get_country_name(country),
                    "data_summary": {
                        "total_fires": int(stats[0]),
                        "date_range": {
                            "start": str(stats[1]),
                            "end": str(stats[2])
                        },
                        "years_available": years,
                        "avg_frp": round(float(stats[3]), 2) if stats[3] else None,
                        "satellites": int(stats[4])
                    },
                    "last_updated": datetime.now().isoformat(),
                    "data_sources": ["NASA FIRMS VIIRS"],
                    "resolution": "375m"
                }
                
                # Save metadata
                metadata_file = metadata_dir / f"{country.lower()}.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                logger.info(f"✅ Generated metadata: {metadata_file}")
                return metadata
                
        except Exception as e:
            logger.error(f"Failed to generate metadata for {country}: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_country_name(self, code: str) -> str:
        """Get country name from ISO code."""
        countries = {
            "PAK": "Pakistan",
            "IDN": "Indonesia",
            "BRA": "Brazil",
            "IND": "India",
            "USA": "United States",
            "AUS": "Australia",
            "MYS": "Malaysia",
            "COD": "Democratic Republic of Congo"
        }
        return countries.get(code, code)
    
    async def import_country(self, country: str):
        """
        Import all files for a country.
        
        IMPROVED: Case-insensitive folder matching
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"IMPORTING: {country}")
        logger.info(f"{'='*60}")
        
        # Map country codes to folder names (lowercase for consistency)
        country_folders = {
            "PAK": "pakistan",
            "IDN": "indonesia",
            "BRA": "brazil",
            "IND": "india",
            "USA": "usa",
            "AUS": "australia",
            "MYS": "malaysia",
            "COD": "congo"
        }
        
        folder_name = country_folders.get(country, country.lower())
        historical_dir = self.data_root / "fires" / "historical"
        
        # Try to find folder (case-insensitive)
        country_dir = None
        if historical_dir.exists():
            for potential_dir in historical_dir.iterdir():
                if potential_dir.is_dir() and potential_dir.name.lower() == folder_name:
                    country_dir = potential_dir
                    break
        
        if not country_dir or not country_dir.exists():
            logger.warning(f"Country directory not found: {folder_name}")
            logger.warning(f"  Looked in: {historical_dir}")
            logger.warning(f"  Expected folder: {folder_name} (case-insensitive)")
            return
        
        # Find all CSV files in country directory
        csv_files = list(country_dir.glob("*.csv"))
        
        if not csv_files:
            logger.warning(f"No CSV files found in: {country_dir}")
            return
        
        logger.info(f"Found {len(csv_files)} file(s) in {country_dir.name}:")
        
        # Parse file info
        files = []
        for csv_file in csv_files:
            filename_no_ext = csv_file.stem
            parts = filename_no_ext.split('_')
            
            if len(parts) >= 5:
                try:
                    year_part = parts[4].replace('.csv', '').strip()
                    
                    file_info = {
                        "path": csv_file,
                        "country": parts[0].upper(),
                        "satellite": parts[3],
                        "year": int(year_part)
                    }
                    files.append(file_info)
                    logger.info(f"  - {csv_file.name} ({file_info['year']}, {file_info['satellite']})")
                except (ValueError, IndexError) as e:
                    logger.warning(f"  ⚠️  Skipping invalid filename: {csv_file.name}")
        
        if not files:
            logger.warning(f"No valid fire data files found")
            return
        
        country_stats = {"imported": 0, "errors": 0, "files": []}
        
        # Import each file
        for file_info in sorted(files, key=lambda x: x['year']):
            result = await self.import_csv(file_info)
            country_stats["imported"] += result.get("imported", 0)
            country_stats["errors"] += result.get("errors", 0)
            country_stats["files"].append(result)
        
        self.stats["countries"][country] = country_stats
        self.stats["files_processed"] += len(files)
        self.stats["total_imported"] += country_stats["imported"]
        self.stats["total_errors"] += country_stats["errors"]
        
        # Generate metadata
        logger.info(f"\n📊 Generating metadata for {country}...")
        await self.generate_metadata(country)
        
        logger.info(f"\n✅ {country} import complete:")
        logger.info(f"   Files: {len(files)}")
        logger.info(f"   Imported: {country_stats['imported']:,}")
        logger.info(f"   Errors: {country_stats['errors']:,}")


async def main():
    """Main import workflow."""
    print("\n" + "="*60)
    print("🔥 GEOWISE - Historical Fire Data Import")
    print("="*60)
    
    # Setup paths - ABSOLUTE PATH
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent
    data_root = project_root / "backend" / "data"
    
    print(f"\n📂 Paths:")
    print(f"   Script: {script_dir}")
    print(f"   Project: {project_root}")
    print(f"   Data: {data_root}")
    print(f"   Data exists: {data_root.exists()}")
    
    if not data_root.exists():
        print(f"\n❌ Data directory not found: {data_root}")
        print(f"   Expected: {project_root / 'backend' / 'data'}")
        return
    
    # Initialize importer
    importer = FireImporter(data_root)
    
    # Discover available files
    all_files = importer.discover_files()
    
    historical_dir = data_root / "fires" / "historical"
    print(f"\n🔍 Historical directory: {historical_dir}")
    print(f"   Exists: {historical_dir.exists()}")
    
    if not all_files:
        print("\n❌ No CSV files found in data/fires/historical/")
        print("   Expected structure: data/fires/historical/{country}/{country}_fires_*.csv")
        print(f"\n   Checking directories:")
        if historical_dir.exists():
            for subdir in historical_dir.iterdir():
                if subdir.is_dir():
                    csv_count = len(list(subdir.glob("*.csv")))
                    print(f"   - {subdir.name}: {csv_count} CSV file(s)")
        return
    
    # Show discovered files
    print(f"\n📁 Discovered {len(all_files)} file(s):")
    countries = set(f['country'] for f in all_files)
    for country in sorted(countries):
        country_files = [f for f in all_files if f['country'] == country]
        print(f"\n  {country}:")
        for f in country_files:
            print(f"    - {f['path'].name} ({f['year']})")
    
    # Confirm import
    print("\n" + "="*60)
    proceed = input("⚠️  Proceed with import? (yes/no): ")
    
    if proceed.lower() != 'yes':
        print("❌ Import cancelled.")
        return
    
    # Initialize database
    print("\n🔧 Initializing database...")
    await init_db()
    
    # Import each country
    for country in sorted(countries):
        await importer.import_country(country)
    
    # Final summary
    print("\n" + "="*60)
    print("🎉 IMPORT COMPLETE!")
    print("="*60)
    print(f"Files processed: {importer.stats['files_processed']}")
    print(f"Total imported: {importer.stats['total_imported']:,}")
    print(f"Total errors: {importer.stats['total_errors']:,}")
    print(f"\nCountries imported: {len(importer.stats['countries'])}")
    for country, stats in importer.stats['countries'].items():
        print(f"  {country}: {stats['imported']:,} fires")
    
    print("\n✅ Database ready for historical analysis!")
    print("   You can now run queries like:")
    print("   - 'What were peak fire months in Brazil 2019?'")
    print("   - 'Show me intense fires in Indonesia 2015'")
    print("   - 'Analyze fire-deforestation correlation in Brazil'")
    
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())