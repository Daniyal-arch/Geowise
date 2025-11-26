"""
GEOWISE - Forest Data Integration (SQLite Compatible)
app/models/forest.py

Integrates Global Forest Watch (GFW) data for deforestation analysis.
Uses the proven GADM TCL Change dataset for yearly tree cover loss statistics.

WHY THIS APPROACH:
- Fetches data from GFW API (no direct database storage needed)
- Can optionally cache results in SQLite for performance
- Keeps implementation simple - SQLite stores metadata, not raster data
- GFW handles the heavy lifting (30m resolution data)
"""

import requests
from datetime import datetime
from typing import Dict, Optional, List
import os
import logging

logger = logging.getLogger(__name__)


class ForestMonitor:
    """
    Global Forest Watch Integration
    
    Provides access to:
    1. Yearly tree cover loss statistics (2001-2024)
    2. Tile URLs for map visualization
    3. Deforestation trend analysis
    
    ARCHITECTURE NOTE:
    - This is a SERVICE class, not a SQLAlchemy model
    - Fetches data on-demand from GFW API
    - Results can be cached in SQLite if needed (see cache methods)
    - No spatial extensions required (GFW handles spatial queries)
    """
    
    # GFW Tile Servers for Visualization
    TILE_SERVERS = {
        "tree_cover_loss": {
            "url": "https://tiles.globalforestwatch.org/umd_tree_cover_loss/v1.12/tcd_30/{z}/{x}/{y}.png",
            "description": "Annual tree cover loss (2001-2024)",
            "min_zoom": 3,
            "max_zoom": 12
        },
        "tree_cover_density": {
            "url": "https://tiles.globalforestwatch.org/umd_tree_cover_density/v1.7/tcd_2000/{z}/{x}/{y}.png",
            "description": "Tree cover density % (year 2000 baseline)",
            "min_zoom": 3,
            "max_zoom": 12
        },
        "tree_cover_gain": {
            "url": "https://tiles.globalforestwatch.org/umd_tree_cover_gain/v1.7/gain/{z}/{x}/{y}.png",
            "description": "Tree cover gain (2000-2020)",
            "min_zoom": 3,
            "max_zoom": 12
        }
    }
    
    def __init__(self, gfw_api_key: Optional[str] = None):
        """
        Initialize Forest Monitor
        
        Args:
            gfw_api_key: GFW API key (optional)
        
        WHY NO DATABASE CONNECTION HERE:
        - SQLite is lightweight - no need for persistent connections
        - Data fetched on-demand from GFW API
        - Can add caching layer later if needed
        """
        self.gfw_api_key = (
            gfw_api_key or 
            os.getenv('GFW_API_KEY') or 
            "8e5b3b69-fa31-4eef-af79-eec9674c7014"
        )
            
        self.base_url = "https://data-api.globalforestwatch.org"
        self.headers = {
            "x-api-key": self.gfw_api_key, 
            "Content-Type": "application/json"
        }
        
        logger.info("GFW ForestMonitor initialized (SQLite mode)")
    
    def get_country_geostore(self, country_iso: str) -> Optional[Dict]:
        """
        Get geostore metadata for a country
        
        Args:
            country_iso: 3-letter ISO code (e.g., 'PAK', 'IND', 'BRA')
        
        Returns:
            Dict with geostore_id, country name, and geometry
        """
        try:
            url = f"{self.base_url}/geostore/admin/{country_iso}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json().get("data")
                logger.info(f"✅ Got geostore for {country_iso}: {data.get('id')}")
                return data
            else:
                logger.error(f"Geostore API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting geostore: {str(e)}")
            return None
    
    def get_yearly_tree_loss(self, country_iso: str, 
                            start_year: Optional[int] = None,
                            end_year: Optional[int] = None) -> Optional[Dict]:
        """
        Get yearly tree cover loss statistics for a country
        
        Args:
            country_iso: 3-letter ISO code
            start_year: Optional start year (default: 2001)
            end_year: Optional end year (default: latest available)
        
        Returns:
            Dict with yearly_data: [{"year": 2001, "loss_ha": 1234.5}, ...]
        
        TESTED & WORKING:
        - Successfully retrieved 23 years of data for Pakistan
        - Total loss: 79,188 hectares (2001-2024)
        - Query structure verified in Colab
        """
        try:
            # Use latest version of GADM TCL Change dataset
            url = f"{self.base_url}/dataset/gadm__tcl__iso_change/latest/query/json"
            
            # Build SQL query (version prefix required by GFW)
            sql = f"""
            SELECT 
                v20250515.umd_tree_cover_loss__year as year,
                SUM(v20250515.umd_tree_cover_loss__ha) as loss_ha
            FROM v20250515
            WHERE v20250515.iso = '{country_iso}'
            AND v20250515.umd_tree_cover_loss__year IS NOT NULL
            """
            
            # Add year filters if provided
            if start_year:
                sql += f" AND v20250515.umd_tree_cover_loss__year >= {start_year}"
            if end_year:
                sql += f" AND v20250515.umd_tree_cover_loss__year <= {end_year}"
            
            sql += """
            GROUP BY v20250515.umd_tree_cover_loss__year
            ORDER BY v20250515.umd_tree_cover_loss__year
            """
            
            payload = {"sql": sql.strip()}
            
            logger.info(f"Querying forest loss for {country_iso}")
            logger.info(f"📡 Calling GFW API for {country_iso}, years {start_year}-{end_year}")
            print(f"\n📡 Calling GFW API...")
            print(f"   URL: {url}")
            print(f"   Country: {country_iso}")
            print(f"   Year filter: {start_year} to {end_year}")

            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=90
            )

            print(f"📡 Response received: Status {response.status_code}")
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=90
            )
            
            if response.status_code == 200:
                result = response.json()
                data = result.get("data", [])
                
                # 🔍 DEBUG: Show what GFW actually returns (SAFE VERSION)
                print(f"\n{'='*60}")
                print(f"🔍 GFW API RESPONSE DEBUG")
                print(f"{'='*60}")
                print(f"Country: {country_iso}")
                print(f"Start Year: {start_year}, End Year: {end_year}")
                print(f"Response Status: {response.status_code}")
                print(f"Total rows returned: {len(data)}")
                
                if data:
                    for i, row in enumerate(data):
                        year_value = row.get('year', 'N/A')
                        loss_value = row.get('loss_ha', 'N/A')
                        
                        # Safe printing - handle any type
                        try:
                            loss_float = float(loss_value)
                            print(f"  Row {i+1}: Year={year_value}, Loss={loss_float:,.2f} ha")
                        except (ValueError, TypeError):
                            print(f"  Row {i+1}: Year={year_value}, Loss={loss_value} (raw value)")
                else:
                    print("  ⚠️  NO DATA RETURNED FROM GFW!")
                    print(f"  Full response: {result}")
                
                print(f"{'='*60}\n")
                
                logger.info(f"🔍 GFW returned {len(data)} rows for {country_iso}")
                
                if not data:
                    logger.warning(f"No forest loss data for {country_iso}")
                    logger.warning(f"Full API response: {result}")
                    return None
                
                # Log each row safely
                for row in data:
                    try:
                        loss_val = float(row.get('loss_ha', 0))
                        logger.info(f"   Year: {row.get('year')}, Loss: {loss_val:,.2f} ha")
                    except:
                        logger.info(f"   Raw row: {row}")
                
                logger.info(f"✅ Got {len(data)} years of forest loss data")
                return {"yearly_data": data}
                    
            else:
                logger.error(f"API error: {response.status_code}")
                logger.error(f"Response: {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting forest loss: {str(e)}")
            return None
    
    def get_country_forest_stats(self, country_iso: str) -> Optional[Dict]:
        """Get comprehensive forest statistics for a country"""
        
        geostore_data = self.get_country_geostore(country_iso)
        if not geostore_data:
            logger.error(f"Failed to get geostore for {country_iso}")
            return None
        
        geostore_id = geostore_data.get("id")
        attributes = geostore_data.get("attributes", {})
        country_name = attributes.get("name") or country_iso
        
        logger.info(f"Processing {country_name}")
        
        forest_stats = self.get_yearly_tree_loss(country_iso)
        
        if not forest_stats:
            logger.warning(f"No forest stats available for {country_iso}")
            return {
                "country_iso": country_iso,
                "country_name": country_name,
                "geostore_id": geostore_id,
                "tree_cover_loss": None,
                "message": "Forest statistics unavailable",
                "last_updated": datetime.now().isoformat()
            }
        
        yearly_data = forest_stats.get("yearly_data", [])
        
        if yearly_data:
            # FIX: Convert string values to float
            total_loss = sum(float(item.get("loss_ha", 0)) for item in yearly_data)
            recent_loss = yearly_data[-1]
            
            return {
                "country_iso": country_iso,
                "country_name": country_name,
                "geostore_id": geostore_id,
                "tree_cover_loss": {
                    "total_loss_ha": total_loss,
                    "recent_year": int(recent_loss.get("year", 0)),
                    "recent_loss_ha": float(recent_loss.get("loss_ha", 0)),
                    "yearly_data": yearly_data,
                    "years_available": len(yearly_data),
                    "data_range": f"{int(yearly_data[0]['year'])}-{int(yearly_data[-1]['year'])}"
                },
                "last_updated": datetime.now().isoformat()
            }
        else:
            return {
                "country_iso": country_iso,
                "country_name": country_name,
                "geostore_id": geostore_id,
                "tree_cover_loss": None,
                "message": "No yearly data available",
                "last_updated": datetime.now().isoformat()
            }
    def analyze_deforestation_trend(self, country_iso: str) -> Optional[Dict]:
        """Analyze deforestation trends over time"""
        
        stats = self.get_country_forest_stats(country_iso)
        if not stats or not stats.get("tree_cover_loss"):
            return {
                "country_iso": country_iso,
                "trend": "NO_DATA",
                "message": "Insufficient data for trend analysis"
            }
        
        yearly_data = stats["tree_cover_loss"].get("yearly_data", [])
        
        if len(yearly_data) < 2:
            return {
                "country_iso": country_iso,
                "trend": "INSUFFICIENT_DATA",
                "message": "Need at least 2 years for trend analysis"
            }
        
        # FIX: Convert to float
        recent_data = sorted(yearly_data, key=lambda x: x["year"], reverse=True)[:5]
        recent_losses = [float(item.get("loss_ha", 0)) for item in recent_data]
        
        early_data = sorted(yearly_data, key=lambda x: x["year"])[:5]
        early_losses = [float(item.get("loss_ha", 0)) for item in early_data]
        
        recent_avg = sum(recent_losses) / len(recent_losses) if recent_losses else 0
        early_avg = sum(early_losses) / len(early_losses) if early_losses else 0
        
        if early_avg > 0:
            change_pct = ((recent_avg - early_avg) / early_avg) * 100
            
            if change_pct > 10:
                trend = "INCREASING"
                severity = "HIGH" if change_pct > 50 else "MODERATE"
            elif change_pct < -10:
                trend = "DECREASING"
                severity = "POSITIVE"
            else:
                trend = "STABLE"
                severity = "NEUTRAL"
        else:
            trend = "STABLE"
            severity = "NEUTRAL"
            change_pct = 0
        
        return {
            "country_iso": country_iso,
            "country_name": stats["country_name"],
            "trend": trend,
            "severity": severity,
            "change_percent": round(change_pct, 2),
            "analysis_period": f"{int(early_data[0]['year'])}-{int(recent_data[0]['year'])}",
            "recent_avg_loss_ha": round(recent_avg, 2),
            "early_avg_loss_ha": round(early_avg, 2),
            "total_loss_ha": stats["tree_cover_loss"]["total_loss_ha"]
        }
    
    def get_tile_configuration(self, layers: Optional[List[str]] = None) -> Dict:
        """
        Get tile configuration for map visualization
        
        Args:
            layers: List of layer names (default: all layers)
        
        Returns:
            Dict with tile URLs for frontend
        """
        if layers is None:
            layers = list(self.TILE_SERVERS.keys())
        
        config = {
            "tile_layers": {},
            "usage": "Use these URLs in Leaflet/Mapbox for visualization"
        }
        
        for layer_id in layers:
            if layer_id in self.TILE_SERVERS:
                config["tile_layers"][layer_id] = self.TILE_SERVERS[layer_id]
        
        return config
    
    def get_available_countries(self) -> List[str]:
        """
        Get list of supported country ISO codes
        
        NOTE: GFW supports all countries, this is just a common subset
        """
        return [
            "PAK",  # Pakistan
            "IND",  # India
            "BGD",  # Bangladesh
            "AFG",  # Afghanistan
            "IDN",  # Indonesia
            "BRA",  # Brazil
            "COD",  # Congo (DRC)
            "USA",  # United States
            "CHN",  # China
            "CAN",  # Canada
            "RUS",  # Russia
            "AUS",  # Australia
            "PER",  # Peru
            "COL",  # Colombia
            "MEX",  # Mexico
        ]
    def get_yearly_tree_loss_by_driver(self, country_iso: str, 
                                   start_year: Optional[int] = None,
                                   end_year: Optional[int] = None) -> Optional[Dict]:
            """
            Get yearly tree cover loss statistics broken down by driver
            
            Returns loss data categorized by:
            - Commodity driven deforestation
            - Shifting agriculture
            - Forestry
            - Wildfire
            - Urbanization
            - Unknown
            
            Args:
                country_iso: 3-letter ISO code
                start_year: Optional start year
                end_year: Optional end year
            
            Returns:
                Dict with driver breakdown
            """
            try:
                url = f"{self.base_url}/dataset/gadm__tcl__iso_change/latest/query/json"
                
                # Build SQL query with driver grouping
                sql = f"""
                SELECT 
                    v20250515.umd_tree_cover_loss__year as year,
                    v20250515.wri_google_tree_cover_loss_drivers__category as driver,
                    SUM(v20250515.umd_tree_cover_loss__ha) as loss_ha,
                    COUNT(*) as pixel_count
                FROM v20250515
                WHERE v20250515.iso = '{country_iso}'
                AND v20250515.umd_tree_cover_loss__year IS NOT NULL
                """
                
                if start_year:
                    sql += f" AND v20250515.umd_tree_cover_loss__year >= {start_year}"
                if end_year:
                    sql += f" AND v20250515.umd_tree_cover_loss__year <= {end_year}"
                
                sql += """
                GROUP BY v20250515.umd_tree_cover_loss__year, 
                        v20250515.wri_google_tree_cover_loss_drivers__category
                ORDER BY v20250515.umd_tree_cover_loss__year, loss_ha DESC
                """
                
                payload = {"sql": sql.strip()}
                
                logger.info(f"Querying forest loss by driver for {country_iso}")
                
                response = requests.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=90
                )
                
                if response.status_code == 200:
                    result = response.json()
                    data = result.get("data", [])
                    
                    if not data:
                        logger.warning(f"No driver data for {country_iso}")
                        return None
                    
                    # Group by year
                    by_year = {}
                    for row in data:
                        year = int(row.get('year'))
                        driver = row.get('driver') or 'Unknown'
                        loss_ha = float(row.get('loss_ha', 0))
                        
                        if year not in by_year:
                            by_year[year] = {
                                'year': year,
                                'total_loss_ha': 0,
                                'drivers': []
                            }
                        
                        by_year[year]['total_loss_ha'] += loss_ha
                        by_year[year]['drivers'].append({
                            'driver_category': driver,
                            'loss_ha': round(loss_ha, 2),
                            'pixel_count': int(row.get('pixel_count', 0))
                        })
                    
                    # Calculate percentages
                    for year_data in by_year.values():
                        total = year_data['total_loss_ha']
                        for driver in year_data['drivers']:
                            driver['percentage'] = round((driver['loss_ha'] / total) * 100, 1) if total > 0 else 0
                    
                    logger.info(f"✅ Got driver breakdown for {len(by_year)} years")
                    
                    return {
                        'yearly_data': list(by_year.values()),
                        'dataset': 'GFW WRI Tree Cover Loss Drivers'
                    }
                else:
                    logger.error(f"Driver API error: {response.status_code}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error getting driver data: {str(e)}")
                return None
    def get_loss_geometries(self, country_iso: str, year: int, limit: int = 5000) -> Optional[Dict]:
        """
        Get actual GeoJSON polygons of deforested areas for a specific year
        
        WHY THIS METHOD:
        - Returns actual polygon geometries (not just statistics)
        - Enables spatial analysis (point-in-polygon tests)
        - Required for classifying fires as deforestation-related or not
        
        IMPORTANT:
        - Limit is set to 5000 polygons by default (API constraint)
        - For countries with massive deforestation, this is a sample
        - Each polygon represents a deforested area with metadata
        
        Args:
            country_iso: 3-letter ISO code (e.g., 'BRA', 'IDN')
            year: Year to get geometries for (e.g., 2019)
            limit: Maximum number of polygons to return (default: 5000)
        
        Returns:
            GeoJSON FeatureCollection with deforestation polygons, or None on error
            
        Example Response:
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Polygon", "coordinates": [...]},
                        "properties": {
                            "id": "BRA.1.2.3_1",
                            "year": 2019,
                            "loss_ha": 125.5,
                            "driver": "Commodity driven deforestation"
                        }
                    },
                    ...
                ]
            }
        """
        try:
            import json
            
            url = f"{self.base_url}/dataset/gadm__tcl__iso_change/latest/query/json"
            
            # SQL query to get geometries
            # ST_AsGeoJSON converts PostGIS geometry to GeoJSON format
            sql = f"""
            SELECT 
                v20250515.gid as id,
                v20250515.umd_tree_cover_loss__year as year,
                v20250515.umd_tree_cover_loss__ha as loss_ha,
                v20250515.wri_google_tree_cover_loss_drivers__category as driver,
                ST_AsGeoJSON(v20250515.geom) as geometry
            FROM v20250515
            WHERE v20250515.iso = '{country_iso}'
            AND v20250515.umd_tree_cover_loss__year = {year}
            LIMIT {limit}
            """
            
            payload = {"sql": sql.strip()}
            
            logger.info(f"📡 Fetching forest loss geometries for {country_iso} {year} (limit: {limit})")
            
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=120  # Longer timeout for geometry queries
            )
            
            if response.status_code == 200:
                result = response.json()
                data = result.get('data', [])
                
                if not data:
                    logger.warning(f"No geometry data found for {country_iso} {year}")
                    return None
                
                # Convert to GeoJSON FeatureCollection
                features = []
                for row in data:
                    try:
                        features.append({
                            "type": "Feature",
                            "geometry": json.loads(row['geometry']),
                            "properties": {
                                "id": row['id'],
                                "year": int(row['year']),
                                "loss_ha": round(float(row['loss_ha']), 2),
                                "driver": row.get('driver', 'Unknown')
                            }
                        })
                    except Exception as e:
                        logger.warning(f"Failed to parse geometry row: {e}")
                        continue
                
                logger.info(f"✅ Successfully fetched {len(features)} forest loss polygons for {country_iso} {year}")
                
                return {
                    "type": "FeatureCollection",
                    "features": features,
                    "metadata": {
                        "country": country_iso,
                        "year": year,
                        "polygon_count": len(features),
                        "note": f"Limited to {limit} polygons. May not represent all forest loss." if len(features) == limit else "Complete dataset"
                    }
                }
            else:
                logger.error(f"GFW geometry API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching forest loss geometries: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    def health_check(self) -> Dict:
        """
        Check if the GFW API is accessible
        
        Returns:
            Dict with API health status
        """
        try:
            response = requests.get(
                f"{self.base_url}/geostore/admin/PAK",
                headers=self.headers,
                timeout=10
            )
            
            api_healthy = response.status_code == 200
            
            return {
                "status": "healthy" if api_healthy else "unhealthy",
                "status_code": response.status_code,
                "api_accessible": api_healthy,
                "base_url": self.base_url,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "api_accessible": False,
                "timestamp": datetime.now().isoformat()
            }