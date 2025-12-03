"""Fire Detection Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import date, datetime, timedelta

from app.database import get_async_session
from app.database import get_db as get_async_session
from app.models.fires import FireDetection
from app.schemas.fires import (
    FireQueryRequest, FireListResponse, FireDetectionResponse,
    FireAggregationRequest, FireAggregationResponse, FireAggregationCell
)
from app.schemas.common import BoundingBox, PaginationMetadata
from app.core.aggregation import fire_aggregator
from app.core.spatial import spatial_ops
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=FireListResponse)
async def get_fires(
    country_iso: Optional[str] = Query(None, min_length=3, max_length=3),
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lon: Optional[float] = Query(None, ge=-180, le=180),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lon: Optional[float] = Query(None, ge=-180, le=180),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    days: Optional[int] = Query(None, ge=1, le=10),
    min_frp: Optional[float] = Query(None, ge=0),
    confidence: Optional[str] = Query(None, regex="^[lnh]$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_async_session)
):
    """Query fire detections with filters"""
    
    query = select(FireDetection)
    
    if days:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
    
    if start_date and end_date:
        query = query.where(
            FireDetection.acq_date >= datetime.combine(start_date, datetime.min.time()),
            FireDetection.acq_date <= datetime.combine(end_date, datetime.max.time())
        )
    
    if min_lat and min_lon and max_lat and max_lon:
        query = query.where(
            FireDetection.latitude >= min_lat,
            FireDetection.latitude <= max_lat,
            FireDetection.longitude >= min_lon,
            FireDetection.longitude <= max_lon
        )
    
    if min_frp:
        query = query.where(FireDetection.frp >= min_frp)
    
    if confidence:
        query = query.where(FireDetection.confidence == confidence)
    
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)
    
    query = query.offset(offset).limit(limit).order_by(FireDetection.acq_date.desc())
    result = await session.execute(query)
    fires = result.scalars().all()
    
    fire_responses = [
        FireDetectionResponse(
            id=str(fire.id),
            latitude=fire.latitude,
            longitude=fire.longitude,
            h3_index_9=fire.h3_index_9,
            h3_index_5=fire.h3_index_5,
            brightness=fire.brightness,
            bright_ti5=fire.bright_ti5,
            frp=fire.frp,
            confidence=fire.confidence,
            satellite=fire.satellite,
            instrument=fire.instrument,
            acq_date=fire.acq_date,
            acq_time=fire.acq_time,
            daynight=fire.daynight
        )
        for fire in fires
    ]
    
    return FireListResponse(
        fires=fire_responses,
        pagination=PaginationMetadata(
            total=total,
            offset=offset,
            limit=limit,
            has_next=offset + limit < total,
            has_prev=offset > 0
        ),
        summary={
            "total_fires": total,
            "avg_frp": sum(f.frp for f in fires if f.frp) / len([f for f in fires if f.frp]) if fires else 0
        }
    )


@router.post("/aggregate", response_model=FireAggregationResponse)
async def aggregate_fires(
    resolution: int = Query(9, ge=5, le=9),
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lon: Optional[float] = Query(None, ge=-180, le=180),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lon: Optional[float] = Query(None, ge=-180, le=180),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    days: Optional[int] = Query(7, ge=1, le=10),
    session: AsyncSession = Depends(get_async_session)
):
    """Aggregate fires by H3 cells"""
    
    if days and not (start_date and end_date):
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
    
    if not start_date or not end_date:
        raise HTTPException(status_code=400, detail="Date range required")
    
    h3_cells = None
    if min_lat and min_lon and max_lat and max_lon:
        bbox = BoundingBox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon)
        h3_cells = list(spatial_ops.bbox_to_h3_cells(bbox, resolution))
    
    aggregated = await fire_aggregator.aggregate_by_h3(
        session=session,
        resolution=resolution,
        start_date=start_date,
        end_date=end_date,
        h3_cells=h3_cells
    )
    
    cells = [FireAggregationCell(**cell) for cell in aggregated]
    
    return FireAggregationResponse(
        cells=cells,
        metadata={
            "resolution": resolution,
            "date_range": f"{start_date} to {end_date}",
            "total_cells": len(cells)
        },
        summary={
            "total_fires": sum(c.fire_count for c in cells),
            "cells_with_fires": len(cells),
            "avg_fires_per_cell": sum(c.fire_count for c in cells) / len(cells) if cells else 0
        }
    )


@router.get("/stats")
async def get_fire_stats(
    start_date: date,
    end_date: date,
    session: AsyncSession = Depends(get_async_session)
):
    """Get fire statistics summary"""
    
    query = select(
        func.count(FireDetection.id).label("total"),
        func.avg(FireDetection.frp).label("avg_frp"),
        func.max(FireDetection.frp).label("max_frp"),
        func.sum(func.case((FireDetection.confidence == 'h', 1), else_=0)).label("high_conf")
    ).where(
        FireDetection.acq_date >= datetime.combine(start_date, datetime.min.time()),
        FireDetection.acq_date <= datetime.combine(end_date, datetime.max.time())
    )
    
    result = await session.execute(query)
    row = result.one()
    
    return {
        "total_fires": row.total,
        "avg_frp": float(row.avg_frp) if row.avg_frp else 0,
        "max_frp": float(row.max_frp) if row.max_frp else 0,
        "high_confidence_count": row.high_conf,
        "date_range": {"start": str(start_date), "end": str(end_date)}
    }
@router.get("/live/{country_iso}")
async def get_live_fires(
    country_iso: str,
    days: int = Query(2, ge=1, le=10, description="Days to look back (1-10)"),
    satellite: str = Query("VIIRS_SNPP_NRT", description="Satellite source"),
    min_frp: Optional[float] = Query(None, ge=0, description="Minimum FRP filter"),
    confidence: Optional[str] = Query(None, regex="^[lnh]$", description="Confidence filter"),
):
    """
    Get LIVE fire detections directly from NASA FIRMS API.
    No database required - fetches real-time data.
    """
    from app.services.nasa_firms import NASAFIRMSService
    from app.config import settings
    
    try:
        logger.info(f"Fetching live fires for {country_iso} (last {days} days)")
        
        # Fetch directly from NASA FIRMS
        async with NASAFIRMSService(settings.NASA_FIRMS_API_KEY) as firms:
            fires = await firms.get_fires_by_country(
                country_iso=country_iso.upper(),
                days=days,
                satellite=satellite
            )
        
        # Apply filters
        if min_frp:
            fires = [f for f in fires if f.frp and f.frp >= min_frp]
        
        if confidence:
            fires = [f for f in fires if f.confidence == confidence]
        
        # Calculate statistics
        total_fires = len(fires)
        
        if total_fires == 0:
            return {
                "success": True,
                "fires": [],
                "statistics": {
                    "total_fires": 0,
                    "country": country_iso.upper(),
                    "date_range": f"Last {days} days",
                    "message": "No active fires detected"
                }
            }
        
        # Calculate stats
        frp_values = [f.frp for f in fires if f.frp]
        brightness_values = [f.brightness for f in fires]
        
        high_conf = len([f for f in fires if f.confidence == 'h'])
        nominal_conf = len([f for f in fires if f.confidence == 'n'])
        low_conf = len([f for f in fires if f.confidence == 'l'])
        
        day_fires = len([f for f in fires if f.daynight == 'D'])
        night_fires = len([f for f in fires if f.daynight == 'N'])
        
        # Group by date
        fires_by_date = {}
        for fire in fires:
            date_str = fire.acq_date.strftime('%Y-%m-%d')
            if date_str not in fires_by_date:
                fires_by_date[date_str] = []
            fires_by_date[date_str].append(fire)
        
        daily_counts = [
            {
                "date": date,
                "count": len(day_fires),
                "avg_frp": sum(f.frp for f in day_fires if f.frp) / len([f for f in day_fires if f.frp]) if any(f.frp for f in day_fires) else 0
            }
            for date, day_fires in sorted(fires_by_date.items())
        ]
        
        # Satellite breakdown
        satellite_breakdown = {}
        for fire in fires:
            sat = fire.satellite
            satellite_breakdown[sat] = satellite_breakdown.get(sat, 0) + 1
        
        # Convert to response format
        fire_responses = [
            {
                "id": str(fire.id),
                "latitude": fire.latitude,
                "longitude": fire.longitude,
                "h3_index_9": fire.h3_index_9,
                "h3_index_5": fire.h3_index_5,
                "brightness": fire.brightness,
                "bright_ti5": fire.bright_ti5,
                "frp": fire.frp,
                "confidence": fire.confidence,
                "satellite": fire.satellite,
                "instrument": fire.instrument,
                "acq_date": fire.acq_date.isoformat(),
                "acq_time": fire.acq_time,
                "daynight": fire.daynight
            }
            for fire in fires
        ]
        
        return {
            "success": True,
            "fires": fire_responses,
            "statistics": {
                "total_fires": total_fires,
                "country": country_iso.upper(),
                "date_range": f"Last {days} days",
                "satellite": satellite,
                
                # Confidence breakdown
                "high_confidence_count": high_conf,
                "nominal_confidence_count": nominal_conf,
                "low_confidence_count": low_conf,
                
                # Intensity stats
                "frp_statistics": {
                    "avg": sum(frp_values) / len(frp_values) if frp_values else 0,
                    "max": max(frp_values) if frp_values else 0,
                    "total": sum(frp_values) if frp_values else 0
                },
                "brightness_statistics": {
                    "avg": sum(brightness_values) / len(brightness_values) if brightness_values else 0,
                    "max": max(brightness_values) if brightness_values else 0
                },
                
                # Temporal
                "fires_by_date": daily_counts,
                "day_fires": day_fires,
                "night_fires": night_fires,
                
                # Sources
                "satellite_breakdown": satellite_breakdown,
                
                "last_updated": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch live fires: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch fires from NASA FIRMS: {str(e)}"
        )