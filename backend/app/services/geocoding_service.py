"""
Geocoding Service - Convert place names to coordinates
Supports multiple providers with fallback
"""

from typing import Optional, List, Dict, Any, Tuple
import httpx
from app.utils.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class GeocodingService:
    """Geocoding service with multiple provider support"""
    
    def __init__(self):
        self.nominatim_base = "https://nominatim.openstreetmap.org"
        self.google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        
    async def geocode_to_bbox(
        self, 
        location_name: str,
        buffer_km: float = 10.0,
        country_hint: Optional[str] = None
    ) -> Optional[List[float]]:
        """
        Convert location name to bounding box
        
        Args:
            location_name: Place name (e.g., "Lahore", "Sindh Province")
            buffer_km: Buffer distance in kilometers (for point locations)
            country_hint: ISO country code for disambiguation (e.g., "PK")
        
        Returns:
            [min_lon, min_lat, max_lon, max_lat] or None
        """
        
        # Try Nominatim first (free, no API key needed)
        bbox = await self._geocode_nominatim(location_name, country_hint)
        
        if not bbox and self.google_api_key:
            # Fallback to Google Maps if available
            bbox = await self._geocode_google(location_name)
        
        if bbox:
            # If bbox is too small (point location), add buffer
            bbox = self._ensure_minimum_bbox(bbox, buffer_km)
            logger.info(f"✅ Geocoded '{location_name}' → {bbox}")
            return bbox
        
        logger.warning(f"⚠️  Could not geocode '{location_name}'")
        return None
    
    async def _geocode_nominatim(
        self, 
        location_name: str,
        country_hint: Optional[str] = None
    ) -> Optional[List[float]]:
        """Geocode using OpenStreetMap Nominatim (free)"""
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                params = {
                    "q": location_name,
                    "format": "json",
                    "limit": 1
                }
                
                if country_hint:
                    params["countrycodes"] = country_hint.lower()
                
                headers = {
                    "User-Agent": "GeoWise-AI/1.0 (contact@geowise.ai)"  # Required by Nominatim
                }
                
                response = await client.get(
                    f"{self.nominatim_base}/search",
                    params=params,
                    headers=headers
                )
                
                if response.status_code == 200:
                    results = response.json()
                    
                    if results:
                        result = results[0]
                        boundingbox = result.get("boundingbox")  # [min_lat, max_lat, min_lon, max_lon]
                        
                        if boundingbox:
                            # Convert to [min_lon, min_lat, max_lon, max_lat]
                            return [
                                float(boundingbox[2]),  # min_lon
                                float(boundingbox[0]),  # min_lat
                                float(boundingbox[3]),  # max_lon
                                float(boundingbox[1])   # max_lat
                            ]
        
        except Exception as e:
            logger.error(f"Nominatim geocoding error: {e}")
        
        return None
    
    async def _geocode_google(self, location_name: str) -> Optional[List[float]]:
        """Geocode using Google Maps API (requires API key)"""
        
        if not self.google_api_key:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://maps.googleapis.com/maps/api/geocode/json",
                    params={
                        "address": location_name,
                        "key": self.google_api_key
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("status") == "OK" and data.get("results"):
                        geometry = data["results"][0]["geometry"]
                        
                        # Check if viewport (bbox) is available
                        if "viewport" in geometry:
                            viewport = geometry["viewport"]
                            return [
                                viewport["southwest"]["lng"],  # min_lon
                                viewport["southwest"]["lat"],  # min_lat
                                viewport["northeast"]["lng"],  # max_lon
                                viewport["northeast"]["lat"]   # max_lat
                            ]
                        
                        # Fallback to location point with buffer
                        elif "location" in geometry:
                            loc = geometry["location"]
                            # Will be buffered by _ensure_minimum_bbox
                            return [loc["lng"], loc["lat"], loc["lng"], loc["lat"]]
        
        except Exception as e:
            logger.error(f"Google geocoding error: {e}")
        
        return None
    
    def _ensure_minimum_bbox(
        self, 
        bbox: List[float], 
        buffer_km: float
    ) -> List[float]:
        """
        Ensure bbox has minimum size (for point locations)
        
        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat]
            buffer_km: Buffer in kilometers
        
        Returns:
            Expanded bbox if needed
        """
        
        min_lon, min_lat, max_lon, max_lat = bbox
        
        # Check if bbox is too small (point location)
        width = max_lon - min_lon
        height = max_lat - min_lat
        
        # Approximate degrees per km at equator (very rough)
        # 1 degree ≈ 111 km
        buffer_degrees = buffer_km / 111.0
        
        # If bbox is smaller than 2x buffer, expand it
        min_width = buffer_degrees * 2
        min_height = buffer_degrees * 2
        
        if width < min_width:
            center_lon = (min_lon + max_lon) / 2
            min_lon = center_lon - buffer_degrees
            max_lon = center_lon + buffer_degrees
        
        if height < min_height:
            center_lat = (min_lat + max_lat) / 2
            min_lat = center_lat - buffer_degrees
            max_lat = center_lat + buffer_degrees
        
        return [min_lon, min_lat, max_lon, max_lat]
    
    async def reverse_geocode(
        self, 
        lon: float, 
        lat: float
    ) -> Optional[Dict[str, Any]]:
        """
        Reverse geocode: coordinates → place name
        
        Args:
            lon: Longitude
            lat: Latitude
        
        Returns:
            Location information dict or None
        """
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.nominatim_base}/reverse",
                    params={
                        "lat": lat,
                        "lon": lon,
                        "format": "json"
                    },
                    headers={
                        "User-Agent": "GeoWise-AI/1.0"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    address = data.get("address", {})
                    
                    return {
                        "display_name": data.get("display_name"),
                        "city": address.get("city") or address.get("town") or address.get("village"),
                        "state": address.get("state"),
                        "country": address.get("country"),
                        "country_code": address.get("country_code", "").upper()
                    }
        
        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
        
        return None


# Singleton instance
geocoding_service = GeocodingService()