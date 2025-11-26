"""
Test Script for GeoWise GEE Integration
========================================
Run this AFTER integrating GEE into your backend

Usage:
    python test_integration.py
"""

import requests
import json

BASE_URL = "http://localhost:8000"  # Your GeoWise backend
TEST_COUNTRY = "PAK"  # Pakistan

def test_gee_health():
    """Test GEE health endpoint"""
    print("\n" + "="*70)
    print("TEST 1: GEE Health Check")
    print("="*70)
    
    try:
        response = requests.get(f"{BASE_URL}/gee/health")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ GEE service is running!")
            print(f"   Status: {data['status']}")
            print(f"   Initialized: {data['initialized']}")
            print(f"   Project: {data.get('project_id', 'N/A')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to backend at {BASE_URL}")
        print("   Make sure your GeoWise backend is running!")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_gee_tiles():
    """Test GEE tiles endpoint"""
    print("\n" + "="*70)
    print(f"TEST 2: Get GEE Tiles for {TEST_COUNTRY}")
    print("="*70)
    
    try:
        print(f"⏳ Requesting tiles for {TEST_COUNTRY}...")
        response = requests.get(f"{BASE_URL}/gee/tiles/{TEST_COUNTRY}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Tiles generated successfully!")
            print(f"\n📍 Country: {data['country_name']} ({data['country_iso']})")
            print(f"   Center: {data['center']}")
            print(f"   Zoom: {data['zoom']}")
            
            print(f"\n🗺️  Available Layers:")
            for layer_name, layer_data in data['layers'].items():
                print(f"\n   {layer_name.upper()}:")
                print(f"   - Name: {layer_data['name']}")
                print(f"   - Year Range: {layer_data['year_range']}")
                print(f"   - Tile URL: {layer_data['tile_url'][:80]}...")
            
            # Save to file
            with open('gee_tiles_test.json', 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n💾 Full response saved to: gee_tiles_test.json")
            
            return data
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_existing_endpoints():
    """Test that existing GFW endpoints still work"""
    print("\n" + "="*70)
    print(f"TEST 3: Verify Existing Endpoints Still Work")
    print("="*70)
    
    try:
        # Test forest endpoint
        print("⏳ Testing existing forest endpoint...")
        response = requests.get(f"{BASE_URL}/forest/statistics/{TEST_COUNTRY}/yearly")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Existing forest endpoint still works!")
            print(f"   Total Loss: {data.get('total_loss_ha', 'N/A')} ha")
            return True
        else:
            print(f"⚠️  Forest endpoint returned: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"⚠️  Could not test existing endpoint: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("GEOWISE GEE INTEGRATION - TEST SUITE")
    print("="*70)
    print(f"Testing backend at: {BASE_URL}")
    print(f"Test country: {TEST_COUNTRY}")
    
    # Test 1: Health check
    health_ok = test_gee_health()
    if not health_ok:
        print("\n❌ GEE service not available. Cannot continue tests.")
        print("\nMake sure you:")
        print("1. Copied gee_service.py to backend/services/")
        print("2. Copied gee_router.py to backend/routers/gee.py")
        print("3. Updated main.py to initialize GEE")
        print("4. Placed gee-service-account-key.json in backend/")
        print("5. Restarted your backend")
        return
    
    # Test 2: Get tiles
    tiles = test_gee_tiles()
    
    # Test 3: Existing endpoints
    test_existing_endpoints()
    
    # Summary
    print("\n" + "="*70)
    print("✅ TEST SUMMARY")
    print("="*70)
    
    if tiles:
        print("\n🎉 SUCCESS! GEE is integrated into your backend!")
        print("\n📋 Next Steps:")
        print("   1. Open gee_tiles_test.json to see the tile URLs")
        print("   2. Update your frontend Dashboard to use these tiles")
        print("   3. Add layer toggles and map visualization")
        
        print("\n📖 Frontend Integration:")
        print("   const response = await fetch(`http://localhost:8000/gee/tiles/${countryISO}`);")
        print("   const data = await response.json();")
        print("   // Then add layers to your map using data.layers")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()