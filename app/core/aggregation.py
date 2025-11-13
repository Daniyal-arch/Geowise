"""
GEOWISE Data Aggregation
Aggregate fire data at different H3 resolutions
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from collections import defaultdict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fires import FireDetection
from app.core.spatial import spatial_ops
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FireAggregator:
    """Aggregate fire detections at H3 resolutions."""
    
    @staticmethod
    async def aggregate_by_h3(
        session: AsyncSession,
        resolution: int,
        start_date: date,
        end_date: date,
        h3_cells: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Aggregate fires by H3 cells."""
        
        h3_field = getattr(FireDetection, f"h3_index_{resolution}")
        
        query = select(
            h3_field.label("h3_index"),
            func.count(FireDetection.id).label("fire_count"),
            func.sum(FireDetection.frp).label("total_frp"),
            func.avg(FireDetection.frp).label("avg_frp"),
            func.max(FireDetection.frp).label("max_frp"),
            func.avg(FireDetection.brightness).label("avg_brightness"),
            func.sum(func.case((FireDetection.confidence == 'h', 1), else_=0)).label("high_confidence_count"),
            func.sum(func.case((FireDetection.confidence == 'n', 1), else_=0)).label("nominal_confidence_count"),
            func.sum(func.case((FireDetection.confidence == 'l', 1), else_=0)).label("low_confidence_count")
        ).where(
            FireDetection.acq_date >= datetime.combine(start_date, datetime.min.time()),
            FireDetection.acq_date <= datetime.combine(end_date, datetime.max.time())
        ).group_by(h3_field)
        
        if h3_cells:
            query = query.where(h3_field.in_(h3_cells))
        
        result = await session.execute(query)
        rows = result.all()
        
        aggregated = []
        for row in rows:
            lat, lon = spatial_ops.h3_to_lat_lon(row.h3_index)
            aggregated.append({
                "h3_index": row.h3_index,
                "resolution": resolution,
                "fire_count": row.fire_count,
                "total_frp": float(row.total_frp) if row.total_frp else None,
                "avg_frp": float(row.avg_frp) if row.avg_frp else None,
                "max_frp": float(row.max_frp) if row.max_frp else None,
                "avg_brightness": float(row.avg_brightness) if row.avg_brightness else None,
                "high_confidence_count": row.high_confidence_count,
                "nominal_confidence_count": row.nominal_confidence_count,
                "low_confidence_count": row.low_confidence_count,
                "centroid_lat": lat,
                "centroid_lon": lon
            })
        
        logger.info(f"Aggregated {len(aggregated)} H3 cells at resolution {resolution}")
        return aggregated
    
    @staticmethod
    async def aggregate_by_time(
        session: AsyncSession,
        start_date: date,
        end_date: date,
        interval: str = "daily"
    ) -> List[Dict[str, Any]]:
        """Aggregate fires by time period."""
        
        if interval == "daily":
            date_func = func.date(FireDetection.acq_date)
        elif interval == "weekly":
            date_func = func.strftime('%Y-%W', FireDetection.acq_date)
        elif interval == "monthly":
            date_func = func.strftime('%Y-%m', FireDetection.acq_date)
        else:
            raise ValueError(f"Invalid interval: {interval}")
        
        query = select(
            date_func.label("period"),
            func.count(FireDetection.id).label("fire_count"),
            func.avg(FireDetection.frp).label("avg_frp")
        ).where(
            FireDetection.acq_date >= datetime.combine(start_date, datetime.min.time()),
            FireDetection.acq_date <= datetime.combine(end_date, datetime.max.time())
        ).group_by("period").order_by("period")
        
        result = await session.execute(query)
        return [{"period": row.period, "fire_count": row.fire_count, "avg_frp": float(row.avg_frp) if row.avg_frp else None} for row in result.all()]


fire_aggregator = FireAggregator()