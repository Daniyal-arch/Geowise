"""Test available forest/land cover datasets in MPC"""

import sys
sys.path.append('.')

import requests

def test_forest_datasets():
    """Test forest-related datasets in MPC"""
    
    stac_url = "https://planetarycomputer.microsoft.com/api/stac/v1"
    
    # Datasets that might have forest loss/change data
    forest_datasets = [
        "io-lulc-annual-v02",  # Impact Observatory Land Cover (annual changes!)
        "esa-worldcover",       # ESA WorldCover
        "alos-fnf-mosaic",     # ALOS Forest/Non-Forest
        "modis-64A1-061",      # MODIS Burned Area (useful for fire correlation!)
    ]
    
    print("🔍 Testing Forest/Land Cover Datasets in MPC...")
    print("=" * 70)
    
    for dataset_id in forest_datasets:
        print(f"\n📊 Dataset: {dataset_id}")
        print("-" * 70)
        
        # Get collection info
        collection_url = f"{stac_url}/collections/{dataset_id}"
        response = requests.get(collection_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"   ✅ Available!")
            print(f"   Title: {data.get('title')}")
            print(f"   Description: {data.get('description', '')[:100]}...")
            
            # Get temporal extent
            extent = data.get('extent', {})
            temporal = extent.get('temporal', {}).get('interval', [[None, None]])[0]
            spatial = extent.get('spatial', {}).get('bbox', [[]])[0]
            
            print(f"   Time range: {temporal[0]} to {temporal[1]}")
            if spatial:
                print(f"   Spatial: Global" if len(spatial) == 4 else f"   Spatial: Regional")
            
            # Try to search for Brazil 2019
            search_url = f"{stac_url}/search"
            brazil_bbox = [-73.9872, -33.7683, -34.7299, 5.2842]
            
            search_params = {
                "collections": [dataset_id],
                "bbox": brazil_bbox,
                "datetime": "2019-01-01/2019-12-31",
                "limit": 1
            }
            
            search_response = requests.post(search_url, json=search_params, timeout=30)
            
            if search_response.status_code == 200:
                results = search_response.json()
                features = results.get('features', [])
                
                if features:
                    print(f"   ✅ Has data for Brazil 2019!")
                    print(f"      Assets: {list(features[0].get('assets', {}).keys())}")
                else:
                    print(f"   ⚠️ No data for Brazil 2019")
            else:
                print(f"   ❌ Search failed: {search_response.status_code}")
        else:
            print(f"   ❌ Not found: {response.status_code}")
    
    print("\n" + "=" * 70)
    print("💡 RECOMMENDATION")
    print("=" * 70)
    print("""
Based on MPC availability, here are your options:

OPTION 1: Use Impact Observatory Annual Land Cover (io-lulc-annual-v02)
✅ 10m resolution (better than Hansen!)
✅ Annual updates (2017-2023)
✅ 9-class classification including forest
✅ Can detect forest loss year-by-year
✅ FREE via MPC

OPTION 2: Use ESA WorldCover (esa-worldcover)
✅ 10m resolution
✅ Global coverage
✅ Recent data (2020, 2021)
✅ FREE via MPC

OPTION 3: Keep using GFW API for Hansen data
✅ Already working
✅ Has driver breakdown
✅ Statistics are sufficient for correlation

RECOMMENDED: HYBRID APPROACH
- GFW API: Statistics + driver breakdown (keep current implementation)
- Impact Observatory: Actual pixels for spatial correlation (add new)
- Result: Best of both worlds!
    """)

if __name__ == "__main__":
    test_forest_datasets()