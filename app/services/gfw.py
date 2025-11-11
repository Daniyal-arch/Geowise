"""
Global Forest Watch (GFW) service for forest monitoring data.

API Documentation: https://data-api.globalforestwatch.org/
Tile Documentation: https://tiles.globalforestwatch.org/
"""

from typing import Dict, List, Optional
from datetime import datetime

from app.services.base import BaseService
from app.models.forest import ForestMonitor
from app.utils.logger import get_logger
from app.utils.exceptions import GFWAPIError, DataValidationError

logger = get_logger(__name__)


class GFWService(BaseService):
    """
    Global Forest Watch API client.
    
    Provides:
    - Country-level forest statistics (yearly tree cover loss 2001-2024)
    - Deforestation trend analysis
    - Tile layer configuration for frontend visualization
    - Forest cover alerts
    
    Data Sources:
    - UMD (University of Maryland) tree cover loss dataset
    - Hansen Global Forest Change
    - GLAD alerts
    
    Resolution:
    - 30m pixels (tiles)
    - Country-level aggregates (API)
    """

    VALID_YEARS = range(2001, 2025)
    TILE_LAYERS = {
        "tree_cover_loss": "umd_tree_cover_loss/v1.9/tcd_30",
        "tree_cover_gain": "umd_tree_cover_gain/v1.9/tcd_30",
        "tree_cover_2000": "umd_tree_cover_2000/v1.9/tcd_30",
        "tree_cover_height": "gfw_forest_height/v1/height",
    }

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            base_url="https://data-api.globalforestwatch.org",
            api_key=api_key,
            timeout=60,
            max_retries=3,
            rate_limit_per_second=2.0,
            cache_ttl_seconds=86400,
        )
        self.forest_monitor = ForestMonitor(api_key=api_key)
        self.tiles_base_url = "https://tiles.globalforestwatch.org"

    async def health_check(self) -> bool:
        """Check if GFW API is available."""
        try:
            await self.get_forest_stats("USA", start_year=2020, end_year=2021)
            return True
        except Exception as e:
            logger.error(f"GFW health check failed: {str(e)}")
            return False

    def _validate_year_range(self, start_year: int, end_year: int):
        """Validate year range parameters."""
        if start_year not in self.VALID_YEARS or end_year not in self.VALID_YEARS:
            raise DataValidationError(
                f"Years must be between {min(self.VALID_YEARS)} and {max(self.VALID_YEARS)}",
                field="year_range",
            )

        if start_year > end_year:
            raise DataValidationError(
                "start_year must be less than or equal to end_year",
                field="year_range",
            )

    async def get_forest_stats(
        self,
        country_iso: str,
        start_year: int = 2001,
        end_year: int = 2024,
    ) -> Dict:
        """
        Get yearly forest loss statistics for a country.
        
        Args:
            country_iso: ISO 3166-1 alpha-3 country code (e.g., 'PAK', 'BRA')
            start_year: Start year (2001-2024)
            end_year: End year (2001-2024)
            
        Returns:
            Dict with yearly forest loss data:
            {
                'country_iso': 'PAK',
                'years': [2001, 2002, ...],
                'tree_loss_ha': [1000.5, 1200.3, ...],
                'tree_loss_km2': [10.0, 12.0, ...],
                'total_loss_ha': 50000.0,
                'total_loss_km2': 500.0,
                'avg_annual_loss_ha': 2500.0
            }
            
        Raises:
            DataValidationError: Invalid parameters
            GFWAPIError: API request failed
        """
        self._validate_year_range(start_year, end_year)

        country_iso = country_iso.upper()

        logger.info(
            f"Fetching forest stats for {country_iso}",
            extra={
                "country": country_iso,
                "start_year": start_year,
                "end_year": end_year,
            },
        )

        try:
            yearly_data = await self._fetch_with_retry(
                self.forest_monitor.get_yearly_tree_loss,
                country_iso,
                start_year,
                end_year,
            )

            if not yearly_data:
                raise GFWAPIError(
                    f"No forest data available for {country_iso}",
                    service_name="Global Forest Watch",
                )

            total_loss_ha = sum(year_data["tree_loss_ha"] for year_data in yearly_data)
            num_years = len(yearly_data)

            result = {
                "country_iso": country_iso,
                "years": [year_data["year"] for year_data in yearly_data],
                "tree_loss_ha": [year_data["tree_loss_ha"] for year_data in yearly_data],
                "tree_loss_km2": [year_data["tree_loss_km2"] for year_data in yearly_data],
                "total_loss_ha": total_loss_ha,
                "total_loss_km2": total_loss_ha / 100,
                "avg_annual_loss_ha": total_loss_ha / num_years if num_years > 0 else 0,
            }

            logger.info(
                f"Retrieved forest stats for {country_iso}",
                extra={
                    "total_loss_ha": total_loss_ha,
                    "years": num_years,
                },
            )

            return result

        except Exception as e:
            if not isinstance(e, (DataValidationError, GFWAPIError)):
                raise GFWAPIError(
                    f"Failed to fetch forest stats: {str(e)}",
                    service_name="Global Forest Watch",
                ) from e
            raise

    async def analyze_deforestation_trend(
        self,
        country_iso: str,
        start_year: int = 2001,
        end_year: int = 2024,
    ) -> Dict:
        """
        Analyze deforestation trend over time.
        
        Args:
            country_iso: ISO 3166-1 alpha-3 country code
            start_year: Start year for trend analysis
            end_year: End year for trend analysis
            
        Returns:
            Dict with trend analysis:
            {
                'country_iso': 'PAK',
                'trend': 'INCREASING',  # or 'DECREASING', 'STABLE'
                'severity': 'HIGH',  # or 'MODERATE', 'LOW'
                'avg_annual_loss_ha': 2500.0,
                'total_loss_ha': 50000.0,
                'peak_year': 2020,
                'peak_loss_ha': 5000.0
            }
        """
        self._validate_year_range(start_year, end_year)

        country_iso = country_iso.upper()

        logger.info(
            f"Analyzing deforestation trend for {country_iso}",
            extra={"country": country_iso, "period": f"{start_year}-{end_year}"},
        )

        try:
            trend_data = await self._fetch_with_retry(
                self.forest_monitor.analyze_deforestation_trend,
                country_iso,
                start_year,
                end_year,
            )

            if not trend_data:
                raise GFWAPIError(
                    f"No trend data available for {country_iso}",
                    service_name="Global Forest Watch",
                )

            logger.info(
                f"Deforestation trend for {country_iso}: {trend_data['trend']}",
                extra=trend_data,
            )

            return trend_data

        except Exception as e:
            if not isinstance(e, (DataValidationError, GFWAPIError)):
                raise GFWAPIError(
                    f"Failed to analyze deforestation trend: {str(e)}",
                    service_name="Global Forest Watch",
                ) from e
            raise

    def get_tile_configuration(
        self,
        layers: Optional[List[str]] = None,
    ) -> Dict:
        """
        Get tile layer URLs for frontend visualization.
        
        Args:
            layers: List of layer names to include. If None, returns all layers.
                   Valid layers: tree_cover_loss, tree_cover_gain, tree_cover_2000, tree_cover_height
                   
        Returns:
            Dict with tile configuration:
            {
                'base_url': 'https://tiles.globalforestwatch.org',
                'layers': {
                    'tree_cover_loss': {
                        'url': 'https://tiles.globalforestwatch.org/umd_tree_cover_loss/v1.9/tcd_30/{z}/{x}/{y}.png',
                        'min_zoom': 3,
                        'max_zoom': 12,
                        'attribution': '...'
                    },
                    ...
                }
            }
        """
        if layers is None:
            layers = list(self.TILE_LAYERS.keys())

        invalid_layers = set(layers) - set(self.TILE_LAYERS.keys())
        if invalid_layers:
            raise DataValidationError(
                f"Invalid layers: {invalid_layers}. Valid: {list(self.TILE_LAYERS.keys())}",
                field="layers",
            )

        tile_config = {
            "base_url": self.tiles_base_url,
            "layers": {},
        }

        for layer_name in layers:
            layer_path = self.TILE_LAYERS[layer_name]
            tile_config["layers"][layer_name] = {
                "url": f"{self.tiles_base_url}/{layer_path}/{{z}}/{{x}}/{{y}}.png",
                "min_zoom": 3,
                "max_zoom": 12,
                "attribution": "© Global Forest Watch / University of Maryland",
                "tile_size": 256,
            }

        logger.info(
            f"Generated tile configuration for {len(layers)} layers",
            extra={"layers": layers},
        )

        return tile_config

    async def get_country_geostore(self, country_iso: str) -> Dict:
        """
        Get geostore metadata for a country.
        
        Args:
            country_iso: ISO 3166-1 alpha-3 country code
            
        Returns:
            Dict with geostore metadata (geometry, area, etc.)
        """
        country_iso = country_iso.upper()

        logger.info(f"Fetching geostore for {country_iso}")

        try:
            geostore = await self._fetch_with_retry(
                self.forest_monitor.get_country_geostore,
                country_iso,
            )

            logger.info(
                f"Retrieved geostore for {country_iso}",
                extra={"has_geometry": "geometry" in geostore},
            )

            return geostore

        except Exception as e:
            raise GFWAPIError(
                f"Failed to fetch geostore for {country_iso}: {str(e)}",
                service_name="Global Forest Watch",
            ) from e

    async def _fetch_with_retry(self, func, *args, **kwargs):
        """
        Execute a ForestMonitor method with retry logic.
        
        This wraps synchronous ForestMonitor methods to make them work with
        our async retry infrastructure.
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    def get_supported_countries(self) -> List[str]:
        """
        Get list of supported country codes.
        
        Note: In production, this should fetch from GFW API.
        For now, returns common countries with forest data.
        """
        return [
            "USA",
            "BRA",
            "CAN",
            "RUS",
            "CHN",
            "AUS",
            "IND",
            "IDN",
            "COD",
            "PER",
            "PAK",
            "ARG",
            "COL",
            "VEN",
            "BOL",
            "MEX",
            "NGA",
            "TZA",
            "MYS",
            "THA",
        ]