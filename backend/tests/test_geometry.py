"""
Fire-Forest Overlap Test - Amazon Region Only
==============================================

Fixed version that:
1. Filters for fires in Amazon rainforest (where MPC has coverage)
2. Uses correct coordinate order [lon, lat, lon, lat]
3. Tests hexagons with fires in MPC-covered areas
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import time
from collections import defaultdict
import numpy as np

from sqlalchemy import select, func, and_
import h3
import requests
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
import planetary_computer as pc

from app.database import init_db, database_manager
from app.models.fires import FireDetection


# ============================================================================
# AMAZON REGION BOUNDARIES (where MPC has coverage)
# ============================================================================

AMAZON_BOUNDS = {
    'lat_min': -15,  # Southern edge
    'lat_max': 5,    # Northern edge  
    'lon_min': -75,  # Western edge
    'lon_max': -45   # Eastern edge
}


async def get_amazon_fires(year: int = 2019):
    """Get fires from Amazon region only (where MPC has coverage)."""
    
    print(f"\n📂 Reading fires from Amazon region...")
    print(f"   Region: Lat {AMAZON_BOUNDS['lat_min']} to {AMAZON_BOUNDS['lat_max']}")
    print(f"           Lon {AMAZON_BOUNDS['lon_min']} to {AMAZON_BOUNDS['lon_max']}")
    print(f"   Year: {year}")
    
    async with database_manager.async_session_maker() as session:
        query = select(
            FireDetection.latitude,
            FireDetection.longitude,
            FireDetection.h3_index_5,
            FireDetection.frp
        ).where(
            and_(
                FireDetection.country == 'BRA',
                func.extract('year', FireDetection.acq_date) == year,
                FireDetection.latitude >= AMAZON_BOUNDS['lat_min'],
                FireDetection.latitude <= AMAZON_BOUNDS['lat_max'],
                FireDetection.longitude >= AMAZON_BOUNDS['lon_min'],
                FireDetection.longitude <= AMAZON_BOUNDS['lon_max']
            )
        )
        
        result = await session.execute(query)
        fires = result.all()
        
        print(f"   ✅ Found {len(fires):,} fires in Amazon region")
        return fires


def group_fires_by_hex(fires: list) -> dict:
    """Group fires by H3 hexagon."""
    
    print(f"\n🔷 Grouping into H3 hexagons...")
    
    hex_data = defaultdict(lambda: {'count': 0, 'total_frp': 0.0, 'fires': []})
    
    for lat, lon, h3_5, frp in fires:
        hex_data[h3_5]['count'] += 1
        hex_data[h3_5]['total_frp'] += (frp or 0)
        hex_data[h3_5]['fires'].append((lat, lon, frp))
    
    print(f"   ✅ Grouped into {len(hex_data):,} hexagons")
    
    # Show top hexagons
    top = sorted(hex_data.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
    print(f"\n   Top 5 hexagons by fire count:")
    for h3_idx, data in top:
        sample_fire = data['fires'][0]
        print(f"      {h3_idx}: {data['count']:,} fires at ({sample_fire[0]:.2f}, {sample_fire[1]:.2f})")
    
    return dict(hex_data)


def get_hex_bbox(h3_index: str) -> list:
    """
    Get bbox [west, south, east, north] for H3 hexagon.
    CRITICAL: Bbox is [lon, lat, lon, lat] NOT [lat, lon, lat, lon]!
    """
    if hasattr(h3, 'cell_to_boundary'):
        boundary = h3.cell_to_boundary(h3_index)
    else:
        boundary = h3.h3_to_geo_boundary(h3_index, geo_json=True)
    
    # Boundary is list of (lat, lon) tuples
    lats = [coord[0] for coord in boundary]
    lons = [coord[1] for coord in boundary]
    
    # Bbox format: [west, south, east, north] = [min_lon, min_lat, max_lon, max_lat]
    bbox = [min(lons), min(lats), max(lons), max(lats)]
    
    return bbox


def query_mpc_for_hex(h3_index: str, year: int, fire_sample: tuple) -> dict:
    """
    Query MPC for forest data in a hexagon.
    Now with better error handling and trying all items.
    """
    bbox = get_hex_bbox(h3_index)
    
    try:
        # Search STAC
        stac_url = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
        search_params = {
            "collections": ["io-lulc-annual-v02"],
            "bbox": bbox,
            "datetime": f"{year}-01-01/{year}-12-31",
            "limit": 5
        }
        
        response = requests.post(stac_url, json=search_params, timeout=30)
        
        if response.status_code != 200:
            return None
        
        items = response.json().get('features', [])
        
        if not items:
            return None
        
        # Try each item until we find one that works
        for item in items:
            try:
                signed_item = pc.sign(item)
                data_url = signed_item['assets']['data']['href']
                
                # Read data
                with rasterio.open(data_url) as src:
                    west, south, east, north = bbox
                    transformed = transform_bounds('EPSG:4326', src.crs, west, south, east, north)
                    
                    # Check overlap
                    bounds = src.bounds
                    overlap_west = max(transformed[0], bounds.left)
                    overlap_south = max(transformed[1], bounds.bottom)
                    overlap_east = min(transformed[2], bounds.right)
                    overlap_north = min(transformed[3], bounds.top)
                    
                    if overlap_west >= overlap_east or overlap_south >= overlap_north:
                        # No overlap, try next item
                        continue
                    
                    # Calculate window
                    window = from_bounds(
                        overlap_west, overlap_south, overlap_east, overlap_north,
                        src.transform
                    )
                    
                    # Limit size for speed
                    max_pixels = 100_000
                    if window.width * window.height > max_pixels:
                        scale = np.sqrt(max_pixels / (window.width * window.height))
                        window = rasterio.windows.Window(
                            window.col_off, window.row_off,
                            int(window.width * scale),
                            int(window.height * scale)
                        )
                    
                    # Read data
                    data = src.read(1, window=window)
                    
                    if data.size == 0:
                        continue
                    
                    # Calculate forest %
                    total = data.size
                    forest = (data == 2).sum()
                    forest_pct = (forest / total) * 100
                    
                    return {
                        'forest_pct': forest_pct,
                        'forest_pixels': int(forest),
                        'total_pixels': int(total),
                        'item_id': item.get('id')
                    }
            
            except Exception:
                # Try next item
                continue
        
        # All items failed
        return None
    
    except Exception:
        return None


async def test_amazon_fire_forest_overlap():
    """Test fire-forest overlap for Amazon region fires."""
    
    print("\n" + "="*70)
    print("🔥🌲 FIRE-FOREST OVERLAP - AMAZON REGION")
    print("="*70)
    print("\nWhy Amazon only?")
    print("  - Your top fire hexagons are in southern/coastal Brazil")
    print("  - MPC has poor coverage there")
    print("  - Amazon rainforest has excellent MPC coverage")
    print("  - Testing where fires + MPC coverage overlap")
    print("="*70)
    
    await init_db()
    
    # Get Amazon fires
    fires = await get_amazon_fires(2019)
    
    if not fires:
        print("\n❌ No fires found in Amazon region!")
        return
    
    # Group by hexagon
    hex_data = group_fires_by_hex(fires)
    
    # Test top 10 hexagons
    top_hexes = sorted(hex_data.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
    
    print(f"\n🎯 Testing TOP 10 Amazon hexagons...")
    print("="*70)
    
    results = []
    
    for i, (h3_idx, fire_info) in enumerate(top_hexes, 1):
        sample_fire = fire_info['fires'][0]
        
        print(f"\n[{i}/10] Hex: {h3_idx}")
        print(f"        Fires: {fire_info['count']:,}")
        print(f"        Location: ({sample_fire[0]:.2f}, {sample_fire[1]:.2f})")
        
        start = time.time()
        forest_data = query_mpc_for_hex(h3_idx, 2019, sample_fire)
        elapsed = time.time() - start
        
        if forest_data:
            print(f"        ✅ Forest: {forest_data['forest_pct']:.1f}% ({elapsed:.1f}s)")
            
            results.append({
                'h3_index': h3_idx,
                'fire_count': fire_info['count'],
                'total_frp': fire_info['total_frp'],
                'forest_pct': forest_data['forest_pct'],
                'location': f"({sample_fire[0]:.2f}, {sample_fire[1]:.2f})",
                'query_time': elapsed
            })
        else:
            print(f"        ❌ MPC query failed ({elapsed:.1f}s)")
        
        time.sleep(0.5)
    
    # Summary
    print("\n" + "="*70)
    print("📊 RESULTS")
    print("="*70)
    
    if results:
        print(f"\n{'Hex':<17} {'Fires':<8} {'Location':<20} {'Forest %':<10}")
        print("-"*70)
        
        for r in results:
            print(
                f"{r['h3_index']:<17} "
                f"{r['fire_count']:<8,} "
                f"{r['location']:<20} "
                f"{r['forest_pct']:<10.1f}"
            )
        
        avg_forest = sum(r['forest_pct'] for r in results) / len(results)
        avg_time = sum(r['query_time'] for r in results) / len(results)
        total_fires = sum(r['fire_count'] for r in results)
        
        print("\n" + "-"*70)
        print(f"Successful queries: {len(results)}/10")
        print(f"Total fires: {total_fires:,}")
        print(f"Average forest: {avg_forest:.1f}%")
        print(f"Average query time: {avg_time:.1f}s")
        
        # Extrapolate
        success_rate = len(results) / 10
        total_amazon_hexes = len(hex_data)
        estimated_successful = int(total_amazon_hexes * success_rate)
        estimated_time = (estimated_successful * avg_time) / 60
        
        print(f"\n💡 Extrapolation to all Amazon hexagons:")
        print(f"   Total hexagons: {total_amazon_hexes:,}")
        print(f"   Expected success: {estimated_successful:,} ({success_rate*100:.0f}%)")
        print(f"   Estimated time: {estimated_time:.0f} minutes")
    else:
        print("\n❌ No successful queries!")
        print("\nPossible issues:")
        print("  - MPC coverage gaps in tested areas")
        print("  - Network issues")
        print("  - Need to adjust search strategy")
    
    print("\n" + "="*70)
    print("✅ Test complete!")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_amazon_fire_forest_overlap())