"""Forest Data Endpoints"""

from fastapi import APIRouter, HTTPException, Path
from typing import Optional

from app.models.forest import ForestMonitor
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

forest_monitor = ForestMonitor()


@router.get("/loss/{country_iso}")
async def get_forest_loss(
    country_iso: str = Path(..., min_length=3, max_length=3),
    start_year: Optional[int] = None,
    end_year: Optional[int] = None
):
    """Get forest loss data for a country"""
    
    country_iso = country_iso.upper()
    
    result = forest_monitor.get_yearly_tree_loss(
        country_iso=country_iso,
        start_year=start_year,
        end_year=end_year
    )
    
    if not result:
        raise HTTPException(status_code=404, detail=f"No forest data for {country_iso}")
    
    return result


@router.get("/stats/{country_iso}")
async def get_forest_stats(
    country_iso: str = Path(..., min_length=3, max_length=3)
):
    """Get comprehensive forest statistics"""
    
    country_iso = country_iso.upper()
    
    stats = forest_monitor.get_country_forest_stats(country_iso)
    
    if not stats:
        raise HTTPException(status_code=404, detail=f"No forest data for {country_iso}")
    
    return stats


@router.get("/trend/{country_iso}")
async def get_deforestation_trend(
    country_iso: str = Path(..., min_length=3, max_length=3)
):
    """Analyze deforestation trends"""
    
    country_iso = country_iso.upper()
    
    trend = forest_monitor.analyze_deforestation_trend(country_iso)
    
    if not trend:
        raise HTTPException(status_code=404, detail=f"No trend data for {country_iso}")
    
    return trend


@router.get("/tiles")
async def get_forest_tiles():
    """Get tile configuration for forest layers"""
    
    return forest_monitor.get_tile_configuration()