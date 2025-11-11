"""
NASA FIRMS (Fire Information for Resource Management System) service.

Fetches active fire data from VIIRS and MODIS satellites.
API Documentation: https://firms.modaps.eosdis.nasa.gov/api/area/
"""

from typing import List, Optional
from datetime import datetime, timedelta
import csv
from io import StringIO

from app.services.base import BaseService
from app.models.fires import FireDetection
from app.schemas.common import BoundingBox
from app.utils.logger import get_logger
from app.utils.exceptions import NASAFIRMSAPIError, DataValidationError

logger = get_logger(__name__)


class NASAFIRMSService(BaseService):
    """
    NASA FIRMS API client for active fire detection data.
    
    Satellites:
    - VIIRS_SNPP_NRT: 375m resolution, near real-time (last 10 days)
    - MODIS_NRT: 1km resolution, near real-time (last 10 days)
    
    Limitations:
    - Maximum 10 days historical data (NRT = Near Real-Time)
    - Maximum area: ~50° latitude/longitude span
    - Rate limit: 100 requests per hour
    """

    VALID_SATELLITES = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT"]
    MAX_DAYS = 10
    MAX_BBOX_SPAN = 50.0

    def __init__(self, api_key: str):
        super().__init__(
            base_url="https://firms.modaps.eosdis.nasa.gov/api/area/csv",
            api_key=api_key,
            timeout=60,
            max_retries=3,
            rate_limit_per_second=0.5,
            cache_ttl_seconds=3600,
        )
        self.api_key = api_key

    async def health_check(self) -> bool:
        """Check if NASA FIRMS API is available."""
        try:
            test_bbox = BoundingBox(
                min_lat=30.0,
                min_lon=70.0,
                max_lat=30.1,
                max_lon=70.1,
            )
            await self.get_fires_by_bbox(test_bbox, days=1, satellite="VIIRS_SNPP_NRT")
            return True
        except Exception as e:
            logger.error(f"NASA FIRMS health check failed: {str(e)}")
            return False

    def _validate_bbox(self, bbox: BoundingBox):
        """Validate bounding box constraints."""
        lat_span = bbox.max_lat - bbox.min_lat
        lon_span = bbox.max_lon - bbox.min_lon

        if lat_span > self.MAX_BBOX_SPAN or lon_span > self.MAX_BBOX_SPAN:
            raise DataValidationError(
                f"Bounding box too large. Maximum span: {self.MAX_BBOX_SPAN}° (current: {lat_span:.2f}° x {lon_span:.2f}°)",
                field="bbox",
            )

    def _validate_days(self, days: int):
        """Validate days parameter."""
        if days < 1 or days > self.MAX_DAYS:
            raise DataValidationError(
                f"Days must be between 1 and {self.MAX_DAYS} (NASA FIRMS NRT limitation)",
                field="days",
            )

    def _parse_csv_response(self, csv_text: str, satellite: str) -> List[FireDetection]:
        """
        Parse NASA FIRMS CSV response into FireDetection objects.
        
        CSV columns:
        - latitude, longitude: Fire location
        - brightness (MODIS) / bright_ti4 (VIIRS): Brightness temperature (Kelvin)
        - scan, track: Pixel size (km)
        - acq_date, acq_time: Acquisition datetime (YYYY-MM-DD, HHMM)
        - satellite: Satellite name
        - confidence: Low (l), nominal (n), high (h)
        - version: Data version
        - bright_ti5: Channel 5 brightness (VIIRS only)
        - frp: Fire Radiative Power (MW)
        - daynight: Day (D) or Night (N)
        """
        fires = []
        reader = csv.DictReader(StringIO(csv_text))

        for row in reader:
            try:
                acq_datetime = datetime.strptime(
                    f"{row['acq_date']} {row['acq_time']}", "%Y-%m-%d %H%M"
                )

                brightness_field = "bright_ti4" if "VIIRS" in satellite else "brightness"
                brightness = float(row.get(brightness_field, row.get("brightness", 0)))

                fire = FireDetection(
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    bright_ti4=brightness,
                    scan=float(row.get("scan", 0)),
                    track=float(row.get("track", 0)),
                    acq_datetime=acq_datetime,
                    satellite=row["satellite"],
                    confidence=row["confidence"],
                    version=row.get("version", ""),
                    bright_ti5=float(row.get("bright_ti5", 0)) if "bright_ti5" in row else None,
                    frp=float(row["frp"]) if row.get("frp") else None,
                    daynight=row.get("daynight", "D"),
                )
                fires.append(fire)

            except (KeyError, ValueError) as e:
                logger.warning(
                    f"Failed to parse fire detection row: {str(e)}",
                    extra={"row": row},
                )
                continue

        return fires

    async def get_fires_by_bbox(
        self,
        bbox: BoundingBox,
        days: int = 7,
        satellite: str = "VIIRS_SNPP_NRT",
    ) -> List[FireDetection]:
        """
        Retrieve fire detections within a bounding box.
        
        Args:
            bbox: Geographic bounding box
            days: Number of days to look back (1-10)
            satellite: Satellite source (VIIRS_SNPP_NRT, VIIRS_NOAA20_NRT, MODIS_NRT)
            
        Returns:
            List of FireDetection objects
            
        Raises:
            DataValidationError: Invalid bbox or days
            NASAFIRMSAPIError: API request failed
        """
        self._validate_bbox(bbox)
        self._validate_days(days)

        if satellite not in self.VALID_SATELLITES:
            raise DataValidationError(
                f"Invalid satellite. Choose from: {', '.join(self.VALID_SATELLITES)}",
                field="satellite",
            )

        bbox_str = f"{bbox.min_lat},{bbox.min_lon},{bbox.max_lat},{bbox.max_lon}"
        endpoint = f"{self.api_key}/{satellite}/{bbox_str}/{days}"

        logger.info(
            f"Fetching fires from NASA FIRMS",
            extra={
                "bbox": bbox_str,
                "days": days,
                "satellite": satellite,
            },
        )

        try:
            csv_data = await self.get(endpoint, use_cache=True)

            if not isinstance(csv_data, str):
                raise NASAFIRMSAPIError(
                    "Expected CSV response from NASA FIRMS",
                    service_name="NASA FIRMS",
                )

            if not csv_data.strip():
                logger.info("No fires detected in region")
                return []

            fires = self._parse_csv_response(csv_data, satellite)

            logger.info(
                f"Retrieved {len(fires)} fire detections",
                extra={
                    "count": len(fires),
                    "date_range": f"{days} days",
                    "satellite": satellite,
                },
            )

            return fires

        except Exception as e:
            if not isinstance(e, (DataValidationError, NASAFIRMSAPIError)):
                raise NASAFIRMSAPIError(
                    f"Failed to fetch fires from NASA FIRMS: {str(e)}",
                    service_name="NASA FIRMS",
                ) from e
            raise

    async def get_fires_by_country(
        self,
        country_iso: str,
        days: int = 7,
        satellite: str = "VIIRS_SNPP_NRT",
    ) -> List[FireDetection]:
        """
        Retrieve fire detections for a country.
        
        Note: Uses approximate country bounding boxes. For precise country boundaries,
        use get_fires_by_bbox with actual country geometry.
        
        Args:
            country_iso: ISO 3166-1 alpha-3 country code (e.g., 'PAK', 'USA')
            days: Number of days to look back (1-10)
            satellite: Satellite source
            
        Returns:
            List of FireDetection objects
        """
        bbox = self._get_country_bbox(country_iso)

        logger.info(
            f"Fetching fires for country {country_iso}",
            extra={"country": country_iso, "days": days},
        )

        return await self.get_fires_by_bbox(bbox, days, satellite)

    def _get_country_bbox(self, country_iso: str) -> BoundingBox:
        """
        Get approximate bounding box for a country.
        
        Note: This is a simplified implementation. In production, use a proper
        country boundary database or service.
        """
        country_bboxes = {
            "PAK": BoundingBox(min_lat=23.5, min_lon=60.5, max_lat=37.5, max_lon=77.5),
            "USA": BoundingBox(min_lat=24.0, min_lon=-125.0, max_lat=49.0, max_lon=-66.0),
            "BRA": BoundingBox(min_lat=-33.0, min_lon=-74.0, max_lat=5.0, max_lon=-34.0),
            "AUS": BoundingBox(min_lat=-44.0, min_lon=112.0, max_lat=-10.0, max_lon=154.0),
            "IND": BoundingBox(min_lat=6.0, min_lon=68.0, max_lat=36.0, max_lon=97.0),
            "CHN": BoundingBox(min_lat=18.0, min_lon=73.0, max_lat=54.0, max_lon=135.0),
            "RUS": BoundingBox(min_lat=41.0, min_lon=19.0, max_lat=82.0, max_lon=180.0),
            "CAN": BoundingBox(min_lat=41.0, min_lon=-141.0, max_lat=83.0, max_lon=-52.0),
            "IDN": BoundingBox(min_lat=-11.0, min_lon=95.0, max_lat=6.0, max_lon=141.0),
            "ARG": BoundingBox(min_lat=-55.0, min_lon=-73.0, max_lat=-21.0, max_lon=-53.0),
        }

        country_iso = country_iso.upper()
        if country_iso not in country_bboxes:
            raise DataValidationError(
                f"Country bbox not available for {country_iso}. Use get_fires_by_bbox instead.",
                field="country_iso",
            )

        return country_bboxes[country_iso]

    async def get_recent_fires(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 50.0,
        days: int = 7,
        satellite: str = "VIIRS_SNPP_NRT",
    ) -> List[FireDetection]:
        """
        Get fires near a specific location.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Search radius in kilometers
            days: Number of days to look back
            satellite: Satellite source
            
        Returns:
            List of FireDetection objects within radius
        """
        degrees_per_km = 1.0 / 111.0
        lat_offset = radius_km * degrees_per_km
        lon_offset = radius_km * degrees_per_km / abs(
            1.0 if latitude == 0 else (1.0 / (abs(latitude) / 90.0))
        )

        bbox = BoundingBox(
            min_lat=latitude - lat_offset,
            min_lon=longitude - lon_offset,
            max_lat=latitude + lat_offset,
            max_lon=longitude + lon_offset,
        )

        fires = await self.get_fires_by_bbox(bbox, days, satellite)

        filtered_fires = []
        for fire in fires:
            distance_km = self._haversine_distance(
                latitude, longitude, fire.latitude, fire.longitude
            )
            if distance_km <= radius_km:
                filtered_fires.append(fire)

        logger.info(
            f"Found {len(filtered_fires)} fires within {radius_km}km",
            extra={
                "center": f"{latitude},{longitude}",
                "radius_km": radius_km,
                "total_fetched": len(fires),
            },
        )

        return filtered_fires

    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate distance between two points using Haversine formula.
        
        Returns:
            Distance in kilometers
        """
        from math import radians, sin, cos, sqrt, atan2

        R = 6371.0

        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c