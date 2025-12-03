"""Minimal NASA FIRMS API Test"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.nasa_firms import NASAFIRMSService
from app.schemas.common import BoundingBox
from app.config import settings


async def test_api():
    if not settings.NASA_FIRMS_API_KEY:
        print("❌ NASA_FIRMS_API_KEY not found in .env")
        return
    
    print(f"🔑 Testing API with key: {settings.NASA_FIRMS_API_KEY[:8]}...")
    
    service = NASAFIRMSService(api_key=settings.NASA_FIRMS_API_KEY)
    
    # Australia bbox (always has fires)
    bbox = BoundingBox(min_lat=-35.0, min_lon=140.0, max_lat=-30.0, max_lon=145.0)
    
    print(f"📍 Testing bbox: Australia")
    print(f"📅 Looking back: 2 days")
    
    async with service:
        fires = await service.get_fires_by_bbox(bbox=bbox, days=2, satellite="VIIRS_SNPP_NRT")
        
        print(f"\n✅ Found {len(fires)} fires!")
        
        if fires:
            fire = fires[0]
            print(f"\nSample fire:")
            print(f"  Location: {fire.latitude}, {fire.longitude}")
            print(f"  Brightness: {fire.brightness}K")
            print(f"  FRP: {fire.frp} MW")
            print(f"  Confidence: {fire.confidence}")
        else:
            print("⚠️ No fires found in this region")


if __name__ == "__main__":
    asyncio.run(test_api())