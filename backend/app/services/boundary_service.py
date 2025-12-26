"""
Boundary Service - Global boundary fetching with smart fallback
Works worldwide using Nominatim + bbox expansion
"""

import httpx
from typing import Optional, Dict, Any, List
import asyncio
import math
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BoundaryService:
    """Global boundary service with multiple fallback strategies"""
    
    def __init__(self):
        self.nominatim_url = "https://nominatim.openstreetmap.org"
        self.timeout = 30.0
    
    async def get_city_boundary(
        self,
        city_name: str,
        country: Optional[str] = None,
        admin_level: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get city boundary with multi-strategy fallback
        
        Strategy 1: Nominatim polygon (best)
        Strategy 2: Expanded bbox from Nominatim point (works globally)
        Strategy 3: Hardcoded major cities (last resort)
        
        Args:
            city_name: City name
            country: Country name or code
            admin_level: Not used (for compatibility)
        
        Returns:
            Boundary data with polygon
        """
        
        logger.info(f"🌍 Fetching boundary for: {city_name}")
        
        # Strategy 1: Try Nominatim for polygon
        result = await self._fetch_nominatim_boundary(city_name, country)
        if result:
            logger.info(f"✅ Got boundary from Nominatim: {result['area_km2']:.0f} km²")
            return result
        
        # Strategy 2: Try Nominatim for point, then expand to bbox
        result = await self._fetch_nominatim_point_expanded(city_name, country)
        if result:
            logger.info(f"✅ Got expanded boundary from point: {result['area_km2']:.0f} km²")
            return result
        
        # Strategy 3: Hardcoded fallback for major cities
        result = self._get_hardcoded_boundary(city_name)
        if result:
            logger.info(f"✅ Using hardcoded boundary: {result['area_km2']:.0f} km²")
            return result
        
        logger.warning(f"❌ Could not fetch boundary for {city_name}")
        return None
    
    async def _fetch_nominatim_boundary(
        self,
        city_name: str,
        country: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Strategy 1: Fetch polygon boundary from Nominatim
        """
        
        try:
            search_query = f"{city_name}, {country}" if country else city_name
            
            params = {
                "q": search_query,
                "format": "json",
                "polygon_geojson": 1,
                "limit": 10
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.nominatim_url}/search",
                    params=params,
                    headers={"User-Agent": "GeoWise-AI/1.0"}
                )
            
            if response.status_code != 200:
                return None
            
            results = response.json()
            
            if not results:
                return None
            
            # Find result with polygon
            for result in results:
                geojson = result.get("geojson")
                
                if not geojson:
                    continue
                
                geom_type = geojson.get("type")
                
                if geom_type in ["Polygon", "MultiPolygon"]:
                    # Extract coordinates
                    if geom_type == "Polygon":
                        coords = geojson["coordinates"][0]
                    else:
                        # Take largest polygon from MultiPolygon
                        coords = max(geojson["coordinates"], key=lambda p: len(p[0]))[0]
                    
                    # Calculate bbox and area
                    lons = [c[0] for c in coords]
                    lats = [c[1] for c in coords]
                    bbox = [min(lons), min(lats), max(lons), max(lats)]
                    area_km2 = (max(lons) - min(lons)) * (max(lats) - min(lats)) * 111 * 111
                    
                    return {
                        "name": city_name,
                        "boundary": {
                            "type": "Polygon",
                            "coordinates": [coords]
                        },
                        "bbox": bbox,
                        "area_km2": round(area_km2, 2),
                        "source": "Nominatim (Polygon)"
                    }
            
            return None
        
        except Exception as e:
            logger.error(f"Nominatim polygon fetch failed: {e}")
            return None
    
    async def _fetch_nominatim_point_expanded(
        self,
        city_name: str,
        country: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Strategy 2: Get point from Nominatim, expand to reasonable boundary
        
        This works for ANY city worldwide!
        """
        
        try:
            search_query = f"{city_name}, {country}" if country else city_name
            
            params = {
                "q": search_query,
                "format": "json",
                "limit": 1
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.nominatim_url}/search",
                    params=params,
                    headers={"User-Agent": "GeoWise-AI/1.0"}
                )
            
            if response.status_code != 200:
                return None
            
            results = response.json()
            
            if not results:
                return None
            
            result = results[0]
            
            # Get point coordinates
            lat = float(result["lat"])
            lon = float(result["lon"])
            
            # Get city type to determine expansion radius
            city_type = result.get("type", "city")
            place_rank = result.get("place_rank", 16)
            
            # Intelligent radius based on city type
            radius_km = self._calculate_expansion_radius(city_type, place_rank)
            
            # Expand to bbox
            bbox = self._expand_point_to_bbox(lat, lon, radius_km)
            
            # Create rectangular boundary
            coords = [
                [bbox[0], bbox[1]],  # SW
                [bbox[2], bbox[1]],  # SE
                [bbox[2], bbox[3]],  # NE
                [bbox[0], bbox[3]],  # NW
                [bbox[0], bbox[1]],  # Close
            ]
            
            area_km2 = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) * 111 * 111
            
            logger.info(f"Expanded {city_name} point to {radius_km}km radius boundary")
            
            return {
                "name": city_name,
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [coords]
                },
                "bbox": bbox,
                "area_km2": round(area_km2, 2),
                "source": f"Nominatim (Expanded {radius_km}km)"
            }
        
        except Exception as e:
            logger.error(f"Nominatim point expansion failed: {e}")
            return None
    
    def _calculate_expansion_radius(self, city_type: str, place_rank: int) -> float:
        """
        Calculate intelligent expansion radius based on city type
        
        OSM place_rank: 1-30 (lower = more important)
        """
        
        # Type-based radius (km)
        type_radius = {
            "city": 15,
            "town": 8,
            "village": 3,
            "suburb": 5,
            "municipality": 12,
            "administrative": 20,
            "state": 50,
            "country": 100,
        }
        
        base_radius = type_radius.get(city_type, 10)
        
        # Adjust by place rank (major cities have lower rank)
        if place_rank <= 8:  # Major city
            return max(base_radius, 20)
        elif place_rank <= 12:  # Large city
            return max(base_radius, 15)
        elif place_rank <= 16:  # Medium city
            return base_radius
        else:  # Small city/town
            return min(base_radius, 8)
    
    def _expand_point_to_bbox(
        self,
        lat: float,
        lon: float,
        radius_km: float
    ) -> List[float]:
        """
        Expand point to bounding box
        
        Args:
            lat: Latitude
            lon: Longitude
            radius_km: Radius in kilometers
        
        Returns:
            [min_lon, min_lat, max_lon, max_lat]
        """
        
        # Convert km to degrees (rough approximation)
        lat_offset = radius_km / 111.0
        lon_offset = radius_km / (111.0 * math.cos(math.radians(lat)))
        
        return [
            lon - lon_offset,  # min_lon
            lat - lat_offset,  # min_lat
            lon + lon_offset,  # max_lon
            lat + lat_offset,  # max_lat
        ]
    
    def _get_hardcoded_boundary(self, city_name: str) -> Optional[Dict[str, Any]]:
        """
        Strategy 3: Hardcoded boundaries for major cities (last resort)
        """
        
        HARDCODED = {
            # Pakistan
            "lahore": {
                "coords": [[74.1847, 31.6340], [74.4462, 31.6217], [74.5051, 31.4732],
                          [74.4380, 31.3204], [74.2431, 31.2641], [74.0847, 31.3455],
                          [73.9993, 31.4903], [74.0993, 31.5903], [74.1847, 31.6340]],
                "bbox": [73.9993, 31.2641, 74.5051, 31.6340],
                "area": 1772.0
            },
            # Add more major cities as needed
        }
        
        key = city_name.lower().strip()
        data = HARDCODED.get(key)
        
        if not data:
            return None
        
        return {
            "name": city_name,
            "boundary": {
                "type": "Polygon",
                "coordinates": [data["coords"]]
            },
            "bbox": data["bbox"],
            "area_km2": data["area"],
            "source": "Hardcoded"
        }


# Singleton
boundary_service = BoundaryService()