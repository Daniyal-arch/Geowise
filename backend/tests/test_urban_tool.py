
import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'f:\\Geo_LLM\\geowise\\backend'))

from app.llm.tools.urban_expansion_tool import analyze_urban_expansion

async def test_tool():
    print("Testing Urban Expansion Tool...")
    try:
        # Test 1: Known City
        print("\n1. Testing Known City (Dubai)...")
        result = await analyze_urban_expansion.invoke({
            "location_name": "Dubai",
            "start_year": 2000,
            "end_year": 2020
        })
        
        if result.get("status") == "success":
            print("✅ Success!")
            print(f"   Name: {result['location']['name']}")
            print(f"   Stats: {result.get('statistics')}")
            print(f"   SDG: {result.get('un_sdg_11_3_1')}")
        else:
            print(f"❌ Failed: {result.get('error')}")

        # Test 2: Dynamic Geocoding (if setup allows, otherwise skip or mock)
        # Assuming geocoding service works or fails gracefully
        print("\n2. Testing Dynamic City (Sharjah)...")
        result_dyn = await analyze_urban_expansion.invoke({
            "location_name": "Sharjah", 
            "start_year": 2000, 
            "end_year": 2020
        })
        
        if result_dyn.get("status") == "success":
             print("✅ Success!")
             print(f"   Name: {result_dyn['location']['name']}")
        else:
             print(f"⚠️ Note: {result_dyn.get('error')} (Expected if geocoding service not fully mock/setup)")

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tool())
