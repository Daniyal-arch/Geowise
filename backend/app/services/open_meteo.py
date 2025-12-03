"""
Open-Meteo service for historical climate data.

API Documentation: https://open-meteo.com/en/docs/historical-weather-api
"""

from typing import Dict, List, Optional
from datetime import datetime, date

from app.services.base import BaseService
from app.models.climate import ClimateMonitor
from app.utils.logger import get_logger
from app.utils.exceptions import OpenMeteoAPIError, DataValidationError

logger = get_logger(__name__)


class OpenMeteoService(BaseService):
    """
    Open-Meteo API client for historical climate data.
    
    Provides:
    - Historical daily weather data (1940-present)
    - Temperature, precipitation, wind, humidity
    - Fire risk assessment based on weather conditions
    - Country-level climate summaries
    
    Data Source:
    - ERA5 reanalysis dataset
    - 25km resolution (0.25° grid)
    - Updated daily
    
    Features:
    - Free API (no key required)
    - High availability (>99.9% uptime)
    - Fast response times (<500ms typical)
    """

    VALID_VARIABLES = [
        "temperature_2m_max",
        "temperature_2m_min",
        "temperature_2m_mean",
        "precipitation_sum",
        "precipitation_hours",
        "windspeed_10m_max",
        "windgusts_10m_max",
        "winddirection_10m_dominant",
        "relative_humidity_2m_mean",
        "relative_humidity_2m_max",
        "relative_humidity_2m_min",
        "soil_temperature_0_to_7cm_mean",
        "soil_moisture_0_to_7cm_mean",
    ]

    FIRE_RISK_VARIABLES = [
        "temperature_2m_max",
        "precipitation_sum",
        "windspeed_10m_max",
        "relative_humidity_2m_mean",
    ]

    def __init__(self):
        super().__init__(
            base_url="https://archive-api.open-meteo.com/v1/archive",
            api_key=None,
            timeout=60,
            max_retries=3,
            rate_limit_per_second=5.0,
            cache_ttl_seconds=43200,
        )
        self.climate_monitor = ClimateMonitor()

    async def health_check(self) -> bool:
        """Check if Open-Meteo API is available."""
        try:
            test_date = date(2024, 1, 1)
            await self.get_climate_data(
                latitude=30.0,
                longitude=70.0,
                start_date=test_date,
                end_date=test_date,
            )
            return True
        except Exception as e:
            logger.error(f"Open-Meteo health check failed: {str(e)}")
            return False

    def _validate_coordinates(self, latitude: float, longitude: float):
        """Validate latitude and longitude."""
        if not (-90 <= latitude <= 90):
            raise DataValidationError(
                f"Latitude must be between -90 and 90 (got {latitude})",
                field="latitude",
            )

        if not (-180 <= longitude <= 180):
            raise DataValidationError(
                f"Longitude must be between -180 and 180 (got {longitude})",
                field="longitude",
            )

    def _validate_date_range(self, start_date: date, end_date: date):
        """Validate date range."""
        if start_date > end_date:
            raise DataValidationError(
                "start_date must be less than or equal to end_date",
                field="date_range",
            )

        if start_date > date.today():
            raise DataValidationError(
                "start_date cannot be in the future",
                field="start_date",
            )

        if end_date > date.today():
            raise DataValidationError(
                "end_date cannot be in the future",
                field="end_date",
            )

        min_date = date(1940, 1, 1)
        if start_date < min_date:
            raise DataValidationError(
                f"Historical data only available from {min_date}",
                field="start_date",
            )

    async def get_climate_data(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        variables: Optional[List[str]] = None,
    ) -> Dict:
        """
        Get historical climate data for a specific location.
        
        Args:
            latitude: Location latitude (-90 to 90)
            longitude: Location longitude (-180 to 180)
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            variables: List of climate variables to retrieve. If None, uses default set.
            
        Returns:
            Dict with climate data:
            {
                'latitude': 30.0,
                'longitude': 70.0,
                'start_date': '2024-01-01',
                'end_date': '2024-01-31',
                'daily': {
                    'time': ['2024-01-01', '2024-01-02', ...],
                    'temperature_2m_max': [25.5, 26.3, ...],
                    'precipitation_sum': [0.0, 2.5, ...],
                    ...
                }
            }
            
        Raises:
            DataValidationError: Invalid parameters
            OpenMeteoAPIError: API request failed
        """
        self._validate_coordinates(latitude, longitude)
        self._validate_date_range(start_date, end_date)

        if variables is None:
            variables = self.VALID_VARIABLES

        invalid_vars = set(variables) - set(self.VALID_VARIABLES)
        if invalid_vars:
            raise DataValidationError(
                f"Invalid variables: {invalid_vars}. Valid: {self.VALID_VARIABLES}",
                field="variables",
            )

        logger.info(
            f"Fetching climate data",
            extra={
                "location": f"{latitude},{longitude}",
                "start_date": str(start_date),
                "end_date": str(end_date),
                "variables": len(variables),
            },
        )

        try:
            climate_data = await self._fetch_with_retry(
                self.climate_monitor.get_historical_data,
                latitude,
                longitude,
                start_date,
                end_date,
                variables,
            )

            if not climate_data or "daily" not in climate_data:
                raise OpenMeteoAPIError(
                    "No climate data returned from Open-Meteo",
                    service_name="Open-Meteo",
                )

            logger.info(
                f"Retrieved climate data",
                extra={
                    "days": len(climate_data["daily"].get("time", [])),
                    "variables": list(climate_data["daily"].keys()),
                },
            )

            return climate_data

        except Exception as e:
            if not isinstance(e, (DataValidationError, OpenMeteoAPIError)):
                raise OpenMeteoAPIError(
                    f"Failed to fetch climate data: {str(e)}",
                    service_name="Open-Meteo",
                ) from e
            raise

    async def get_country_climate_summary(
        self,
        country_iso: str,
        start_date: date,
        end_date: date,
        sample_points: int = 10,
    ) -> Dict:
        """
        Get climate summary for an entire country.
        
        Samples multiple points across the country and aggregates results.
        
        Args:
            country_iso: ISO 3166-1 alpha-3 country code
            start_date: Start date
            end_date: End date
            sample_points: Number of points to sample across country
            
        Returns:
            Dict with aggregated climate summary:
            {
                'country_iso': 'PAK',
                'start_date': '2024-01-01',
                'end_date': '2024-01-31',
                'summary': {
                    'avg_temperature_max': 25.5,
                    'avg_temperature_min': 15.3,
                    'total_precipitation': 50.2,
                    'avg_humidity': 65.5,
                    ...
                }
            }
        """
        self._validate_date_range(start_date, end_date)

        country_iso = country_iso.upper()

        logger.info(
            f"Fetching climate summary for {country_iso}",
            extra={
                "country": country_iso,
                "sample_points": sample_points,
                "date_range": f"{start_date} to {end_date}",
            },
        )

        try:
            summary = await self._fetch_with_retry(
                self.climate_monitor.get_country_climate_summary,
                country_iso,
                start_date,
                end_date,
                sample_points,
            )

            logger.info(
                f"Retrieved climate summary for {country_iso}",
                extra=summary.get("summary", {}),
            )

            return summary

        except Exception as e:
            raise OpenMeteoAPIError(
                f"Failed to fetch country climate summary: {str(e)}",
                service_name="Open-Meteo",
            ) from e

    async def assess_fire_risk(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        temperature_threshold: float = 30.0,
        precipitation_threshold: float = 2.0,
        humidity_threshold: float = 40.0,
        wind_threshold: float = 20.0,
    ) -> Dict:
        """
        Assess fire risk based on weather conditions.
        
        Fire risk factors:
        - High temperature (>30°C)
        - Low precipitation (<2mm)
        - Low humidity (<40%)
        - High wind speed (>20 km/h)
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            start_date: Start date
            end_date: End date
            temperature_threshold: Temperature threshold for high risk (°C)
            precipitation_threshold: Precipitation threshold for high risk (mm)
            humidity_threshold: Humidity threshold for high risk (%)
            wind_threshold: Wind speed threshold for high risk (km/h)
            
        Returns:
            Dict with fire risk assessment:
            {
                'latitude': 30.0,
                'longitude': 70.0,
                'period': '2024-01-01 to 2024-01-31',
                'overall_risk': 'HIGH',  # EXTREME, HIGH, MODERATE, LOW
                'risk_days': 15,
                'total_days': 31,
                'risk_percentage': 48.4,
                'factors': {
                    'high_temperature_days': 20,
                    'low_precipitation_days': 25,
                    'low_humidity_days': 18,
                    'high_wind_days': 10
                }
            }
        """
        self._validate_coordinates(latitude, longitude)
        self._validate_date_range(start_date, end_date)

        logger.info(
            f"Assessing fire risk",
            extra={
                "location": f"{latitude},{longitude}",
                "date_range": f"{start_date} to {end_date}",
            },
        )

        try:
            climate_data = await self.get_climate_data(
                latitude=latitude,
                longitude=longitude,
                start_date=start_date,
                end_date=end_date,
                variables=self.FIRE_RISK_VARIABLES,
            )

            risk_assessment = await self._fetch_with_retry(
                self.climate_monitor.assess_fire_risk_conditions,
                climate_data,
                temperature_threshold,
                precipitation_threshold,
                humidity_threshold,
                wind_threshold,
            )

            logger.info(
                f"Fire risk assessment complete",
                extra={
                    "risk_level": risk_assessment["overall_risk"],
                    "risk_days": risk_assessment["risk_days"],
                },
            )

            return risk_assessment

        except Exception as e:
            raise OpenMeteoAPIError(
                f"Failed to assess fire risk: {str(e)}",
                service_name="Open-Meteo",
            ) from e

    async def get_multi_location_data(
        self,
        locations: List[tuple[float, float]],
        start_date: date,
        end_date: date,
        variables: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Fetch climate data for multiple locations in parallel.
        
        Args:
            locations: List of (latitude, longitude) tuples
            start_date: Start date
            end_date: End date
            variables: Climate variables to retrieve
            
        Returns:
            List of climate data dicts (one per location)
        """
        import asyncio

        logger.info(
            f"Fetching climate data for {len(locations)} locations",
            extra={"locations": len(locations)},
        )

        tasks = [
            self.get_climate_data(lat, lon, start_date, end_date, variables)
            for lat, lon in locations
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]

        if failed:
            logger.warning(
                f"{len(failed)} location(s) failed to fetch climate data",
                extra={"failed_count": len(failed)},
            )

        logger.info(
            f"Retrieved climate data for {len(successful)}/{len(locations)} locations"
        )

        return successful

    async def _fetch_with_retry(self, func, *args, **kwargs):
        """
        Execute a ClimateMonitor method with retry logic.
        
        This wraps synchronous ClimateMonitor methods to make them work with
        our async retry infrastructure.
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    def get_supported_variables(self) -> List[str]:
        """Get list of supported climate variables."""
        return self.VALID_VARIABLES.copy()