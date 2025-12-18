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