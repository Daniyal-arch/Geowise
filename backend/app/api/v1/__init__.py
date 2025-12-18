"""GEOWISE API v1"""

from fastapi import APIRouter

# Import with error handling
try:
    from app.api.v1 import health, fires, analysis, forest, climate, tiles, query, mpc, api
    print(" All route modules loaded (including MPC)")
except ImportError as e:
    print(f" Import error: {e}")
    raise

api_router = APIRouter()
"""
GEE Endpoints - Add to your app/api/v1/__init__.py
===================================================

Add these endpoints to your existing api_router.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List
import logging

# Import the GEE service
from app.services.gee_service import gee_service

from app.api.v1 import floods



api_router.include_router(floods.router, prefix="/floods", tags=["Floods"])

logger = logging.getLogger(__name__)

# ============================================================================
# MODELS
# ============================================================================

class TileLayer(BaseModel):
    name: str
    tile_url: str
    description: str
    year_range: str

class GEETilesResponse(BaseModel):
    success: bool
    country_iso: str
    country_name: str
    center: List[float]
    zoom: int
    layers: Dict[str, TileLayer]
    generated_at: str

class GEEHealthResponse(BaseModel):
    service: str
    status: str
    initialized: bool
    project_id: str = None


# ============================================================================

# In your app/api/v1/__init__.py, add these routes:

@api_router.get("/gee/health", response_model=GEEHealthResponse, tags=["GEE"])
async def gee_health_check():
    """Check if Google Earth Engine service is initialized"""
    return GEEHealthResponse(
        service="Google Earth Engine",
        status="healthy" if gee_service.initialized else "not_initialized",
        initialized=gee_service.initialized,
        project_id=gee_service.project_id
    )

@api_router.get("/gee/tiles/{country_iso}", response_model=GEETilesResponse, tags=["GEE"])
async def get_gee_tiles(
    country_iso: str,
    include_lossyear: bool = Query(False, description="Include loss-by-year layer"),
    force_refresh: bool = Query(False, description="Force refresh (ignore cache)")
):
    """
    Get Hansen Global Forest Change map tile URLs
    
    Args:
        country_iso: ISO 3166-1 alpha-3 country code (e.g., 'BRA', 'PAK')
        include_lossyear: Include color-coded loss-by-year layer
        force_refresh: Bypass cache and generate new tiles
    
    Returns:
        Tile URLs for baseline, loss, and gain layers
        
    Example:
        GET /api/v1/gee/tiles/BRA
        GET /api/v1/gee/tiles/PAK?include_lossyear=true
    """
    try:
        logger.info(f"Request for GEE tiles: {country_iso}")
        
        result = gee_service.get_forest_tiles(
            country_iso=country_iso,
            include_lossyear=include_lossyear,
            force_refresh=force_refresh
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting GEE tiles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
# Register all routes
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(fires.router, prefix="/fires", tags=["Fires"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
api_router.include_router(forest.router, prefix="/forest", tags=["Forest"])
api_router.include_router(climate.router, prefix="/climate", tags=["Climate"])
api_router.include_router(tiles.router, prefix="/tiles", tags=["Tiles"])
api_router.include_router(query.router, prefix="/query", tags=["Query"])
api_router.include_router(mpc.router, prefix="/mpc", tags=["MPC"])  # NEW!
api_router.include_router(api.router, prefix="", tags=["Info"])