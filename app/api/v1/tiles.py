"""Map Tile Endpoints"""

from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta
from typing import Optional

from app.database import get_async_session
from app.core.aggregation import fire_aggregator
from app.core.tile_generator import tile_generator
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/fire-density")
async def get_fire_density_tiles(
    resolution: int = Query(9, ge=5, le=9),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    days: int = Query(7, ge=1, le=30),
    session: AsyncSession = Depends(get_async_session)
):
    """Get fire density as GeoJSON tiles"""
    
    if not start_date or not end_date:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
    
    aggregated = await fire_aggregator.aggregate_by_h3(
        session=session,
        resolution=resolution,
        start_date=start_date,
        end_date=end_date
    )
    
    geojson = tile_generator.aggregate_to_geojson(
        aggregated_data=aggregated,
        properties=["fire_count", "avg_frp", "max_frp"]
    )
    
    return geojson


@router.get("/heatmap")
async def get_heatmap_data(
    resolution: int = Query(9, ge=5, le=9),
    days: int = Query(7, ge=1, le=30),
    session: AsyncSession = Depends(get_async_session)
):
    """Get heatmap data [lat, lon, intensity]"""
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    aggregated = await fire_aggregator.aggregate_by_h3(
        session=session,
        resolution=resolution,
        start_date=start_date,
        end_date=end_date
    )
    
    heatmap = tile_generator.generate_heatmap_data(
        aggregated_data=aggregated,
        value_field="fire_count"
    )
    
    return {
        "type": "heatmap",
        "data": heatmap,
        "metadata": {
            "resolution": resolution,
            "date_range": f"{start_date} to {end_date}",
            "total_points": len(heatmap)
        }
    }