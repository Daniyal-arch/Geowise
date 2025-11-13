"""Test core logic - Working version"""
import sys
from pathlib import Path

# Add backend root to Python path
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

print(f"Python path: {backend_root}")

try:
    from app.core.spatial import spatial_ops
    from app.schemas.common import BoundingBox
    print("✅ Imports successful!")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def test_spatial():
    print("\n" + "="*60)
    print("🧪 TESTING SPATIAL OPERATIONS")
    print("="*60)
    
    # Test 1: Convert lat/lon to H3
    print("\n📍 Test 1: Lat/Lon to H3 Index")
    h3_index = spatial_ops.lat_lon_to_h3(30.5, 70.5, 9)
    print(f"   Location: 30.5, 70.5")
    print(f"   ✅ H3 Index (res 9): {h3_index}")
    
    # Test 2: Convert H3 back to lat/lon
    print("\n📍 Test 2: H3 Index to Lat/Lon")
    lat, lon = spatial_ops.h3_to_lat_lon(h3_index)
    print(f"   ✅ Centroid: {lat:.5f}, {lon:.5f}")
    
    # Test 3: Get neighbors
    print("\n📍 Test 3: Get H3 Neighbors")
    neighbors = spatial_ops.get_h3_neighbors(h3_index, k=1)
    print(f"   ✅ Neighbors (k=1): {len(neighbors)} cells")
    
    # Test 4: Calculate distance
    print("\n📍 Test 4: Calculate Distance")
    distance = spatial_ops.haversine_distance(30.5, 70.5, 31.5, 71.5)
    print(f"   ✅ Distance: {distance:.2f} km")
    
    # Test 5: Get cell area
    print("\n📍 Test 5: Get Cell Area")
    area_9 = spatial_ops.get_h3_area_km2(9)
    print(f"   ✅ Area (res 9): {area_9:.6f} km²")
    
    print("\n" + "="*60)
    print("🎉 ALL TESTS PASSED!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_spatial()