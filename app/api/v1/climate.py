"""Climate Data Endpoints"""

from fastapi import APIRouter, HTTPException, Query
from datetime import date
from typing import Optional

from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/temperature")
async def get_temperature_data(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    """Get temperature data for location (Open-Meteo integration)"""
    
    logger.info(f"Fetching temperature for {latitude},{longitude}")
    
    return {
        "location": {"latitude": latitude, "longitude": longitude},
        "date_range": {"start": str(start_date), "end": str(end_date)},
        "data": [
            {"date": str(start_date), "temperature": 28.5, "max_temp": 32.0, "min_temp": 25.0}
        ],
        "source": "Open-Meteo API",
        "note": "Placeholder - implement Open-Meteo service in Phase 7"
    }


@router.get("/precipitation")
async def get_precipitation_data(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    """Get precipitation data for location"""
    
    return {
        "location": {"latitude": latitude, "longitude": longitude},
        "date_range": {"start": str(start_date), "end": str(end_date)},
        "data": [
            {"date": str(start_date), "precipitation_mm": 12.5}
        ],
        "source": "Open-Meteo API"
    }