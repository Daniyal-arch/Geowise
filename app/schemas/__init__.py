"""
GEOWISE Schemas Package
Centralized import location for all Pydantic schemas.

WHY SCHEMAS:
- Input validation (catch errors before they reach your logic)
- Output formatting (consistent API responses)
- Type safety (FastAPI auto-validates and documents)
- Auto-generated OpenAPI/Swagger documentation

USAGE:
    from app.schemas import FireQueryRequest, CorrelationRequest
    from app.schemas.common import BoundingBox, DateRange
"""

# Common schemas (used across multiple endpoints)
from app.schemas.common import (
    # Geographic
    BoundingBox,
    Point,
    
    # Temporal
    DateRange,
    
    # Pagination
    PaginationParams,
    PaginationMetadata,
    
    # H3 Spatial
    H3ResolutionEnum,
    H3Resolution,
    
    # GeoJSON
    GeoJSONPoint,
    GeoJSONPolygon,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    
    # Response wrappers
    SuccessResponse,
    ErrorResponse,
    HealthCheckResponse,
    
    # Enums
    SortOrder,
    TemporalResolution,
    ConfidenceLevel,
    
    # Utilities
    validate_country_iso,
)

# Fire schemas
from app.schemas.fires import (
    # Requests
    FireQueryRequest,
    FireAggregationRequest,
    
    # Responses
    FireDetectionResponse,
    FireListResponse,
    FireAggregationCell,
    FireAggregationResponse,
    FireStatisticsResponse,
    FireGeoJSONResponse,
)

# Forest schemas
from app.schemas.forest import (
    # Requests
    ForestStatsRequest,
    ForestTrendRequest,
    ForestTileRequest,
    
    # Responses
    YearlyForestLoss,
    ForestStatsResponse,
    ForestTrendResponse,
    TileLayerConfig,
    ForestTileResponse,
    ForestHealthCheckResponse,
    AvailableCountriesResponse,
    
    # Enums
    DeforestationTrend,
    TrendSeverity,
)

# Climate schemas
from app.schemas.climate import (
    # Requests
    ClimateQueryRequest,
    ClimateCountrySummaryRequest,
    FireRiskAssessmentRequest,
    
    # Responses
    DailyClimateData,
    ClimateTimeSeriesResponse,
    ClimateStatistics,
    ClimateCountrySummaryResponse,
    FireRiskAssessmentResponse,
    ClimateHealthCheckResponse,
    
    # Enums
    FireRiskLevel,
)

# Analysis schemas
from app.schemas.analysis import (
    # Enums
    AnalysisType,
    RegionType,
    CorrelationMethod,
    
    # Requests
    CorrelationRequest,
    AnalysisListRequest,
    
    # Responses
    StatisticalResults,
    SpatialCellData,
    CorrelationResponse,
    AnalysisSummary,
    AnalysisListResponse,
    CorrelationMapResponse,
)


# Export all schemas
__all__ = [
    # ===== COMMON =====
    # Geographic
    "BoundingBox",
    "Point",
    
    # Temporal
    "DateRange",
    
    # Pagination
    "PaginationParams",
    "PaginationMetadata",
    
    # H3 Spatial
    "H3ResolutionEnum",
    "H3Resolution",
    
    # GeoJSON
    "GeoJSONPoint",
    "GeoJSONPolygon",
    "GeoJSONFeature",
    "GeoJSONFeatureCollection",
    
    # Response wrappers
    "SuccessResponse",
    "ErrorResponse",
    "HealthCheckResponse",
    
    # Enums
    "SortOrder",
    "TemporalResolution",
    "ConfidenceLevel",
    
    # Utilities
    "validate_country_iso",
    
    # ===== FIRES =====
    # Requests
    "FireQueryRequest",
    "FireAggregationRequest",
    
    # Responses
    "FireDetectionResponse",
    "FireListResponse",
    "FireAggregationCell",
    "FireAggregationResponse",
    "FireStatisticsResponse",
    "FireGeoJSONResponse",
    
    # ===== FOREST =====
    # Requests
    "ForestStatsRequest",
    "ForestTrendRequest",
    "ForestTileRequest",
    
    # Responses
    "YearlyForestLoss",
    "ForestStatsResponse",
    "ForestTrendResponse",
    "TileLayerConfig",
    "ForestTileResponse",
    "ForestHealthCheckResponse",
    "AvailableCountriesResponse",
    
    # Enums
    "DeforestationTrend",
    "TrendSeverity",
    
    # ===== CLIMATE =====
    # Requests
    "ClimateQueryRequest",
    "ClimateCountrySummaryRequest",
    "FireRiskAssessmentRequest",
    
    # Responses
    "DailyClimateData",
    "ClimateTimeSeriesResponse",
    "ClimateStatistics",
    "ClimateCountrySummaryResponse",
    "FireRiskAssessmentResponse",
    "ClimateHealthCheckResponse",
    
    # Enums
    "FireRiskLevel",
    
    # ===== ANALYSIS =====
    # Enums
    "AnalysisType",
    "RegionType",
    "CorrelationMethod",
    
    # Requests
    "CorrelationRequest",
    "AnalysisListRequest",
    
    # Responses
    "StatisticalResults",
    "SpatialCellData",
    "CorrelationResponse",
    "AnalysisSummary",
    "AnalysisListResponse",
    "CorrelationMapResponse",
]


# Example usage documentation
"""
EXAMPLE USAGE IN API ROUTES:

from fastapi import APIRouter, Depends
from app.schemas import FireQueryRequest, FireListResponse
from app.database import get_db

router = APIRouter()

@router.get("/fires", response_model=FireListResponse)
async def get_fires(
    query: FireQueryRequest = Depends(),
    db: AsyncSession = Depends(get_db)
):
    # FastAPI automatically validates 'query' against FireQueryRequest schema
    # If validation fails, returns 422 error with details
    
    # Your logic here
    fires = await fetch_fires(query, db)
    
    # FastAPI automatically converts response to FireListResponse format
    return fires
"""