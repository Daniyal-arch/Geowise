"""
External API services for data retrieval.

Services:
- BaseService: Abstract base with retry logic, rate limiting, caching
- NASAFIRMSService: Active fire detection data (VIIRS/MODIS)
- GFWService: Forest monitoring data (Global Forest Watch)
- OpenMeteoService: Historical climate data (ERA5)
- WorldBankService: Country-level statistics (optional)

Usage:
    from app.services import NASAFIRMSService, GFWService, OpenMeteoService
    
    nasa = NASAFIRMSService(api_key="your_key")
    async with nasa:
        fires = await nasa.get_fires_by_country("PAK", days=7)
"""

from app.services.base import BaseService
from app.services.nasa_firms import NASAFIRMSService
from app.services.gfw import GFWService
from app.services.open_meteo import OpenMeteoService
from app.services.worldbank import WorldBankService

__all__ = [
    "BaseService",
    "NASAFIRMSService",
    "GFWService",
    "OpenMeteoService",
    "WorldBankService",
]