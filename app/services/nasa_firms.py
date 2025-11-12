"""
NASA FIRMS (Fire Information for Resource Management System) service.
Fetches active fire data from VIIRS and MODIS satellites.
"""

from typing import List
from datetime import datetime
import csv
from io import StringIO
import asyncio
import aiohttp

from app.models.fires import FireDetection
from app.schemas.common import BoundingBox
from app.utils.logger import get_logger
from app.utils.exceptions import NASAFIRMSAPIError, DataValidationError

logger = get_logger(__name__)


class NASAFIRMSService:
    """NASA FIRMS API client for active fire detection data."""

    VALID_SATELLITES = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT"]
    MAX_DAYS = 10
    MAX_BBOX_SPAN = 50.0

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
        self.session = None

    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
        self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info("HTTP session created for NASAFIRMSService", extra={"base_url": self.base_url})
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def health_check(self) -> bool:
        """Check if NASA FIRMS API is available."""
        try:
            test_bbox = BoundingBox(min_lat=30.0, min_lon=70.0, max_lat=30.1, max_lon=70.1)
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

        # Build URL with correct bbox format (lon,lat,lon,lat)
        bbox_str = bbox.to_string()
        endpoint = f"{self.api_key}/{satellite}/{bbox_str}/{days}"
        full_url = f"{self.base_url}/{endpoint}"

        logger.info(
            f"Fetching fires from NASA FIRMS",
            extra={
                "bbox": bbox_str,
                "days": days,
                "satellite": satellite,
            },
        )

        try:
            async with self.session.get(full_url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise NASAFIRMSAPIError(
                        f"API returned status {response.status}: {error_text}",
                        service_name="NASA FIRMS",
                    )

                csv_data = await response.text()

            if not csv_data.strip():
                logger.info("No fires detected in region")
                return []

            # Validate CSV format
            if not csv_data.startswith("latitude"):
                raise NASAFIRMSAPIError(
                    f"Unexpected response format: {csv_data[:100]}",
                    service_name="NASA FIRMS",
                )

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

        except aiohttp.ClientError as e:
            raise NASAFIRMSAPIError(
                f"HTTP request failed: {str(e)}",
                service_name="NASA FIRMS",
            ) from e
        except asyncio.TimeoutError as e:
            raise NASAFIRMSAPIError(
                "Request timeout - NASA FIRMS API not responding",
                service_name="NASA FIRMS",
            ) from e
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
        
        Uses country-bounding-boxes library to get accurate country boundaries
        for all ISO 3166-1 alpha-3 country codes.
        
        Args:
            country_iso: ISO 3166-1 alpha-3 country code (e.g., 'PAK', 'USA', 'BRA')
            days: Number of days to look back (1-10)
            satellite: Satellite source
            
        Returns:
            List of FireDetection objects
            
        Raises:
            DataValidationError: Invalid country code
        """
        bbox = self._get_country_bbox(country_iso)

        logger.info(
            f"Fetching fires for country {country_iso}",
            extra={"country": country_iso, "days": days},
        )

        return await self.get_fires_by_bbox(bbox, days, satellite)

    def _get_country_bbox(self, country_iso: str) -> BoundingBox:
        """
        Get bounding box for any country using country-bounding-boxes library.
        
        Args:
            country_iso: ISO 3166-1 alpha-3 country code (e.g., 'PAK', 'USA')
            
        Returns:
            BoundingBox for the country
            
        Raises:
            DataValidationError: Invalid or unsupported country code
        """
        try:
            from country_bounding_boxes import country_subunits_by_iso_code
            
            country_iso = country_iso.upper()
            
            # Get country bounding box from library
            country_data = country_subunits_by_iso_code(country_iso)
            
            if not country_data:
                raise DataValidationError(
                    f"Country code '{country_iso}' not found. Please use ISO 3166-1 alpha-3 format (e.g., 'PAK', 'USA')",
                    field="country_iso",
                )
            
            # The library returns a list of subunits (for countries with territories)
            # We'll use the first one (main country) or combine all
            if len(country_data) == 1:
                bbox_data = country_data[0].bbox
            else:
                # Combine all subunits into one bbox
                all_lons = []
                all_lats = []
                for subunit in country_data:
                    all_lons.extend([subunit.bbox[0], subunit.bbox[2]])
                    all_lats.extend([subunit.bbox[1], subunit.bbox[3]])
                
                bbox_data = [min(all_lons), min(all_lats), max(all_lons), max(all_lats)]
            
            # Create BoundingBox
            # Library format: [min_lon, min_lat, max_lon, max_lat]
            bbox = BoundingBox(
                min_lat=bbox_data[1],
                min_lon=bbox_data[0],
                max_lat=bbox_data[3],
                max_lon=bbox_data[2],
            )
            
            logger.info(
                f"Retrieved bbox for {country_iso}",
                extra={
                    "country": country_iso,
                    "bbox": bbox.to_string(),
                    "subunits": len(country_data),
                },
            )
            
            return bbox
            
        except ImportError:
            raise NASAFIRMSAPIError(
                "country-bounding-boxes library not installed. Run: pip install country-bounding-boxes",
                service_name="NASA FIRMS",
            )
        except Exception as e:
            if isinstance(e, DataValidationError):
                raise
            raise DataValidationError(
                f"Failed to get bounding box for country '{country_iso}': {str(e)}",
                field="country_iso",
            ) from e

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
        # Convert radius to degrees (approximate)
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

        # Filter by actual distance using Haversine formula
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
                "filtered": len(filtered_fires),
            },
        )

        return filtered_fires

    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate distance between two points using Haversine formula.
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            
        Returns:
            Distance in kilometers
        """
        from math import radians, sin, cos, sqrt, atan2

        R = 6371.0  # Earth radius in kilometers

        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c