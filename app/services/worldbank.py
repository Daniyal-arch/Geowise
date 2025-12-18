"""
World Bank API service for country-level statistics.

API Documentation: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""

from typing import Dict, List, Optional
from datetime import datetime

from app.services.base import BaseService
from app.utils.logger import get_logger
from app.utils.exceptions import WorldBankAPIError, DataValidationError

logger = get_logger(__name__)


class WorldBankService(BaseService):
    """
    World Bank API client for country-level statistics.
    
    Provides:
    - Forest area statistics
    - Agricultural land data
    - Population data
    - Economic indicators
    - Environmental indicators
    
    Common Indicators:
    - AG.LND.FRST.ZS: Forest area (% of land area)
    - AG.LND.FRST.K2: Forest area (sq. km)
    - AG.LND.AGRI.ZS: Agricultural land (% of land area)
    - EN.ATM.CO2E.PC: CO2 emissions (metric tons per capita)
    - SP.POP.TOTL: Population, total
    """

    FOREST_INDICATORS = {
        "forest_area_pct": "AG.LND.FRST.ZS",
        "forest_area_km2": "AG.LND.FRST.K2",
        "agricultural_land_pct": "AG.LND.AGRI.ZS",
    }

    CLIMATE_INDICATORS = {
        "co2_emissions_per_capita": "EN.ATM.CO2E.PC",
        "methane_emissions": "EN.ATM.METH.KT.CE",
        "renewable_energy_pct": "EG.FEC.RNEW.ZS",
    }

    def __init__(self):
        super().__init__(
            base_url="https://api.worldbank.org/v2",
            api_key=None,
            timeout=30,
            max_retries=3,
            rate_limit_per_second=10.0,
            cache_ttl_seconds=86400,
        )

    async def health_check(self) -> bool:
        """Check if World Bank API is available."""
        try:
            await self.get_indicator_data("USA", "SP.POP.TOTL", start_year=2020, end_year=2020)
            return True
        except Exception as e:
            logger.error(f"World Bank health check failed: {str(e)}")
            return False

    def _validate_year_range(self, start_year: Optional[int], end_year: Optional[int]):
        """Validate year range."""
        if start_year is not None and end_year is not None:
            if start_year > end_year:
                raise DataValidationError(
                    "start_year must be less than or equal to end_year",
                    field="year_range",
                )

            current_year = datetime.now().year
            if end_year > current_year:
                raise DataValidationError(
                    f"end_year cannot be greater than current year ({current_year})",
                    field="end_year",
                )

    async def get_indicator_data(
        self,
        country_iso: str,
        indicator: str,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> Dict:
        """
        Get indicator data for a country.
        
        Args:
            country_iso: ISO 3166-1 alpha-3 country code
            indicator: World Bank indicator code (e.g., 'AG.LND.FRST.K2')
            start_year: Start year (optional, defaults to all available)
            end_year: End year (optional, defaults to all available)
            
        Returns:
            Dict with indicator data:
            {
                'country_iso': 'PAK',
                'country_name': 'Pakistan',
                'indicator': 'AG.LND.FRST.K2',
                'indicator_name': 'Forest area (sq. km)',
                'data': [
                    {'year': 2020, 'value': 1234.5},
                    {'year': 2021, 'value': 1230.0},
                    ...
                ]
            }
            
        Raises:
            DataValidationError: Invalid parameters
            WorldBankAPIError: API request failed
        """
        self._validate_year_range(start_year, end_year)

        country_iso = country_iso.upper()

        date_range = "all"
        if start_year and end_year:
            date_range = f"{start_year}:{end_year}"

        endpoint = f"country/{country_iso}/indicator/{indicator}"
        params = {
            "format": "json",
            "date": date_range,
            "per_page": 1000,
        }

        logger.info(
            f"Fetching World Bank indicator data",
            extra={
                "country": country_iso,
                "indicator": indicator,
                "date_range": date_range,
            },
        )

        try:
            response = await self.get(endpoint, params=params)

            if not isinstance(response, list) or len(response) < 2:
                raise WorldBankAPIError(
                    f"Invalid response format from World Bank API",
                    service_name="World Bank",
                )

            metadata = response[0]
            data = response[1]

            if not data:
                logger.warning(f"No data available for {country_iso} - {indicator}")
                return {
                    "country_iso": country_iso,
                    "country_name": None,
                    "indicator": indicator,
                    "indicator_name": None,
                    "data": [],
                }

            result = {
                "country_iso": country_iso,
                "country_name": data[0].get("country", {}).get("value"),
                "indicator": indicator,
                "indicator_name": data[0].get("indicator", {}).get("value"),
                "data": [
                    {
                        "year": int(item["date"]),
                        "value": item["value"],
                    }
                    for item in data
                    if item["value"] is not None
                ],
            }

            logger.info(
                f"Retrieved {len(result['data'])} data points",
                extra={
                    "country": country_iso,
                    "indicator": indicator,
                },
            )

            return result

        except Exception as e:
            if not isinstance(e, (DataValidationError, WorldBankAPIError)):
                raise WorldBankAPIError(
                    f"Failed to fetch World Bank data: {str(e)}",
                    service_name="World Bank",
                ) from e
            raise

    async def get_forest_statistics(
        self,
        country_iso: str,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> Dict:
        """
        Get forest statistics for a country.
        
        Args:
            country_iso: ISO 3166-1 alpha-3 country code
            start_year: Start year
            end_year: End year
            
        Returns:
            Dict with forest statistics:
            {
                'country_iso': 'PAK',
                'country_name': 'Pakistan',
                'forest_area_pct': {...},
                'forest_area_km2': {...},
                'agricultural_land_pct': {...}
            }
        """
        country_iso = country_iso.upper()

        logger.info(
            f"Fetching forest statistics for {country_iso}",
            extra={"country": country_iso},
        )

        results = {}
        for name, indicator in self.FOREST_INDICATORS.items():
            try:
                data = await self.get_indicator_data(
                    country_iso, indicator, start_year, end_year
                )
                results[name] = data
            except Exception as e:
                logger.warning(
                    f"Failed to fetch {name} for {country_iso}: {str(e)}",
                    extra={"indicator": indicator},
                )
                results[name] = None

        return {
            "country_iso": country_iso,
            "country_name": next(
                (r["country_name"] for r in results.values() if r and r["country_name"]),
                None,
            ),
            **results,
        }

    async def get_climate_indicators(
        self,
        country_iso: str,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> Dict:
        """
        Get climate-related indicators for a country.
        
        Args:
            country_iso: ISO 3166-1 alpha-3 country code
            start_year: Start year
            end_year: End year
            
        Returns:
            Dict with climate indicators
        """
        country_iso = country_iso.upper()

        logger.info(
            f"Fetching climate indicators for {country_iso}",
            extra={"country": country_iso},
        )

        results = {}
        for name, indicator in self.CLIMATE_INDICATORS.items():
            try:
                data = await self.get_indicator_data(
                    country_iso, indicator, start_year, end_year
                )
                results[name] = data
            except Exception as e:
                logger.warning(
                    f"Failed to fetch {name} for {country_iso}: {str(e)}",
                    extra={"indicator": indicator},
                )
                results[name] = None

        return {
            "country_iso": country_iso,
            "country_name": next(
                (r["country_name"] for r in results.values() if r and r["country_name"]),
                None,
            ),
            **results,
        }

    async def get_country_info(self, country_iso: str) -> Dict:
        """
        Get basic country information.
        
        Args:
            country_iso: ISO 3166-1 alpha-3 country code
            
        Returns:
            Dict with country metadata
        """
        country_iso = country_iso.upper()

        endpoint = f"country/{country_iso}"
        params = {"format": "json"}

        logger.info(f"Fetching country info for {country_iso}")

        try:
            response = await self.get(endpoint, params=params)

            if not isinstance(response, list) or len(response) < 2:
                raise WorldBankAPIError(
                    f"Invalid response format from World Bank API",
                    service_name="World Bank",
                )

            data = response[1]

            if not data:
                raise WorldBankAPIError(
                    f"Country {country_iso} not found",
                    service_name="World Bank",
                )

            country = data[0]

            result = {
                "iso2": country.get("iso2Code"),
                "iso3": country.get("id"),
                "name": country.get("name"),
                "region": country.get("region", {}).get("value"),
                "income_level": country.get("incomeLevel", {}).get("value"),
                "capital_city": country.get("capitalCity"),
                "longitude": country.get("longitude"),
                "latitude": country.get("latitude"),
            }

            logger.info(f"Retrieved country info for {country_iso}")

            return result

        except Exception as e:
            if not isinstance(e, WorldBankAPIError):
                raise WorldBankAPIError(
                    f"Failed to fetch country info: {str(e)}",
                    service_name="World Bank",
                ) from e
            raise

    def get_available_indicators(self) -> Dict[str, Dict[str, str]]:
        """
        Get list of available indicators.
        
        Returns:
            Dict with categories of indicators
        """
        return {
            "forest": self.FOREST_INDICATORS,
            "climate": self.CLIMATE_INDICATORS,
        }