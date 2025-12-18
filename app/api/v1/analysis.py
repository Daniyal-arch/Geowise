"""Analysis Endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from typing import List

from app.database import get_async_session
from app.schemas.analysis import CorrelationRequest, CorrelationResponse
from app.core.correlation import correlation_analyzer
from app.core.aggregation import fire_aggregator
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/correlation", response_model=CorrelationResponse)
async def run_correlation(
    request: CorrelationRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Run spatial correlation analysis"""
    
    aggregated = await fire_aggregator.aggregate_by_h3(
        session=session,
        resolution=request.h3_resolution,
        start_date=request.start_date,
        end_date=request.end_date
    )
    
    if len(aggregated) < 10:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient data: {len(aggregated)} cells (minimum 10 required)"
        )
    
    fire_counts = [cell["fire_count"] for cell in aggregated]
    temperatures = [cell.get("avg_brightness", 300) for cell in aggregated]
    
    try:
        result = correlation_analyzer.analyze_fire_temperature(
            fire_data=aggregated,
            temperature_data=[{"temperature": t} for t in temperatures]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    from app.schemas.analysis import StatisticalResults
    
    return CorrelationResponse(
        analysis_id=f"corr_{request.start_date}_{request.end_date}",
        analysis_type=request.analysis_type,
        region={
            "type": request.region_type,
            "identifier": request.region_identifier
        },
        time_period={
            "start": str(request.start_date),
            "end": str(request.end_date)
        },
        statistical_results=StatisticalResults(
            correlation_coefficient=result["correlation_coefficient"],
            p_value=result["p_value"],
            r_squared=result["r_squared"],
            sample_size=result["sample_size"],
            is_significant=result["is_significant"]
        ),
        metadata={
            "resolution": request.h3_resolution,
            "method": str(request.correlation_method)
        },
        created_at=date.today()
    )