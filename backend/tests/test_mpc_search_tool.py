"""
Global Boundary Service Test
Tests cities from different continents
Run: python test_boundary_global_standalone.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Use the exact same class from production
import httpx
from typing import Optional, Dict, Any, List
import math


class BoundaryService:
    """Copy of production boundary service for testing"""
    
    def __init__(self):
        self.nominatim_url = "https://nominatim.openstreetmap.org"
        self.timeout = 30.0
    
    async def get_city_boundary(
        self,
        city_name: str,
        country: Optional[str] = None,
        admin_level: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get boundary with fallback strategies"""
        
        # Strategy 1: Polygon
        result = await self._fetch_nominatim_boundary(city_name, country)
        if result:
            return result
        
        # Strategy 2: Point expansion
        result = await self._fetch_nominatim_point_expanded(city_name, country)
        if result:
            return result
        
        # Strategy 3: Hardcoded
        result = self._get_hardcoded_boundary(city_name)
        if result:
            return result
        
        return None
    
    async def _fetch_nominatim_boundary(self, city_name: str, country: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch polygon from Nominatim"""
        try:
            search_query = f"{city_name}, {country}" if country else city_name
            params = {"q": search_query, "format": "json", "polygon_geojson": 1, "limit": 10}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.nominatim_url}/search", params=params,
                                          headers={"User-Agent": "GeoWise-AI/1.0"})
            
            if response.status_code != 200:
                return None
            
            results = response.json()
            for result in results:
                geojson = result.get("geojson")
                if not geojson:
                    continue
                
                geom_type = geojson.get("type")
                if geom_type in ["Polygon", "MultiPolygon"]:
                    if geom_type == "Polygon":
                        coords = geojson["coordinates"][0]
                    else:
                        coords = max(geojson["coordinates"], key=lambda p: len(p[0]))[0]
                    
                    lons = [c[0] for c in coords]
                    lats = [c[1] for c in coords]
                    bbox = [min(lons), min(lats), max(lons), max(lats)]
                    area_km2 = (max(lons) - min(lons)) * (max(lats) - min(lats)) * 111 * 111
                    
                    return {
                        "name": city_name,
                        "boundary": {"type": "Polygon", "coordinates": [coords]},
                        "bbox": bbox,
                        "area_km2": round(area_km2, 2),
                        "source": "Nominatim (Polygon)"
                    }
            return None
        except:
            return None
    
    async def _fetch_nominatim_point_expanded(self, city_name: str, country: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Expand point to boundary"""
        try:
            search_query = f"{city_name}, {country}" if country else city_name
            params = {"q": search_query, "format": "json", "limit": 1}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.nominatim_url}/search", params=params,
                                          headers={"User-Agent": "GeoWise-AI/1.0"})
            
            if response.status_code != 200 or not response.json():
                return None
            
            result = response.json()[0]
            lat, lon = float(result["lat"]), float(result["lon"])
            city_type = result.get("type", "city")
            place_rank = result.get("place_rank", 16)
            
            radius_km = self._calculate_expansion_radius(city_type, place_rank)
            bbox = self._expand_point_to_bbox(lat, lon, radius_km)
            
            coords = [[bbox[0], bbox[1]], [bbox[2], bbox[1]], [bbox[2], bbox[3]],
                     [bbox[0], bbox[3]], [bbox[0], bbox[1]]]
            
            area_km2 = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) * 111 * 111
            
            return {
                "name": city_name,
                "boundary": {"type": "Polygon", "coordinates": [coords]},
                "bbox": bbox,
                "area_km2": round(area_km2, 2),
                "source": f"Nominatim (Expanded {radius_km}km)"
            }
        except:
            return None
    
    def _calculate_expansion_radius(self, city_type: str, place_rank: int) -> float:
        """Calculate radius based on city type"""
        type_radius = {"city": 15, "town": 8, "village": 3, "suburb": 5, 
                      "municipality": 12, "administrative": 20}
        base_radius = type_radius.get(city_type, 10)
        
        if place_rank <= 8:
            return max(base_radius, 20)
        elif place_rank <= 12:
            return max(base_radius, 15)
        else:
            return base_radius
    
    def _expand_point_to_bbox(self, lat: float, lon: float, radius_km: float) -> List[float]:
        """Expand point to bbox"""
        lat_offset = radius_km / 111.0
        lon_offset = radius_km / (111.0 * math.cos(math.radians(lat)))
        return [lon - lon_offset, lat - lat_offset, lon + lon_offset, lat + lat_offset]
    
    def _get_hardcoded_boundary(self, city_name: str) -> Optional[Dict[str, Any]]:
        """Hardcoded fallback"""
        HARDCODED = {
            "lahore": {
                "coords": [[74.1847, 31.6340], [74.4462, 31.6217], [74.5051, 31.4732],
                          [74.4380, 31.3204], [74.2431, 31.2641], [74.0847, 31.3455],
                          [73.9993, 31.4903], [74.0993, 31.5903], [74.1847, 31.6340]],
                "bbox": [73.9993, 31.2641, 74.5051, 31.6340],
                "area": 1772.0
            }
        }
        
        data = HARDCODED.get(city_name.lower().strip())
        if not data:
            return None
        
        return {
            "name": city_name,
            "boundary": {"type": "Polygon", "coordinates": [data["coords"]]},
            "bbox": data["bbox"],
            "area_km2": data["area"],
            "source": "Hardcoded"
        }


async def main():
    print("\n🌍 " + "="*58 + " 🌍")
    print("🌍   Global Boundary Service Test                      🌍")
    print("🌍 " + "="*58 + " 🌍")
    
    service = BoundaryService()
    
    # Test cities from different continents
    cities = [
        ("Lahore", "Pakistan"),
        ("Karachi", "Pakistan"),
        ("Rawalpindi", "Pakistan"),
        ("Tokyo", "Japan"),
        ("London", "UK"),
        ("New York", "USA"),
        ("Sydney", "Australia"),
        ("Mumbai", "India"),
        ("Lagos", "Nigeria"),
        ("São Paulo", "Brazil"),
    ]
    
    results = {}
    
    for city, country in cities:
        print(f"\n{'='*60}")
        print(f"Testing: {city}, {country}")
        print('='*60)
        
        result = await service.get_city_boundary(city, country)
        results[city] = result
        
        if result:
            print(f"✅ SUCCESS")
            print(f"   Area: {result['area_km2']:,.0f} km²")
            print(f"   Points: {len(result['boundary']['coordinates'][0])}")
            print(f"   Source: {result['source']}")
        else:
            print(f"❌ FAILED")
        
        await asyncio.sleep(1)
    
    # Summary
    print("\n" + "="*60)
    print("📊 GLOBAL TEST SUMMARY")
    print("="*60)
    
    success_count = sum(1 for r in results.values() if r)
    print(f"\nSuccess Rate: {success_count}/{len(cities)} ({success_count/len(cities)*100:.0f}%)")
    
    by_source = {}
    for result in results.values():
        if result:
            source = result['source'].split('(')[0].strip()
            by_source[source] = by_source.get(source, 0) + 1
    
    print(f"\nBy Source:")
    for source, count in sorted(by_source.items()):
        print(f"  {source}: {count}")
    
    if success_count == len(cities):
        print("\n🎉🎉🎉 100% SUCCESS - WORKS GLOBALLY! 🎉🎉🎉")
    elif success_count >= len(cities) * 0.9:
        print("\n✅ Excellent - 90%+ success rate")
    elif success_count >= len(cities) * 0.7:
        print("\n👍 Good - 70%+ success rate")
    else:
        print("\n⚠️  Needs improvement")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())