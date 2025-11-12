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

# Import only common schemas at top level - these don't depend on other schemas
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

# Export all schemas - but don't import the others at module level to avoid circular imports
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


# Lazy imports to avoid circular dependencies
def __getattr__(name):
    """Lazy import schema modules to avoid circular dependencies."""
    if name in {
        # Fire schemas
        "FireQueryRequest", "FireAggregationRequest", "FireDetectionResponse",
        "FireListResponse", "FireAggregationCell", "FireAggregationResponse",
        "FireStatisticsResponse", "FireGeoJSONResponse"
    }:
        from app.schemas.fires import (
            FireQueryRequest, FireAggregationRequest, FireDetectionResponse,
            FireListResponse, FireAggregationCell, FireAggregationResponse,
            FireStatisticsResponse, FireGeoJSONResponse
        )
        return locals()[name]
    
    elif name in {
        # Forest schemas
        "ForestStatsRequest", "ForestTrendRequest", "ForestTileRequest",
        "YearlyForestLoss", "ForestStatsResponse", "ForestTrendResponse",
        "TileLayerConfig", "ForestTileResponse", "ForestHealthCheckResponse",
        "AvailableCountriesResponse", "DeforestationTrend", "TrendSeverity"
    }:
        from app.schemas.forest import (
            ForestStatsRequest, ForestTrendRequest, ForestTileRequest,
            YearlyForestLoss, ForestStatsResponse, ForestTrendResponse,
            TileLayerConfig, ForestTileResponse, ForestHealthCheckResponse,
            AvailableCountriesResponse, DeforestationTrend, TrendSeverity
        )
        return locals()[name]
    
    elif name in {
        # Climate schemas
        "ClimateQueryRequest", "ClimateCountrySummaryRequest", "FireRiskAssessmentRequest",
        "DailyClimateData", "ClimateTimeSeriesResponse", "ClimateStatistics",
        "ClimateCountrySummaryResponse", "FireRiskAssessmentResponse", "ClimateHealthCheckResponse",
        "FireRiskLevel"
    }:
        from app.schemas.climate import (
            ClimateQueryRequest, ClimateCountrySummaryRequest, FireRiskAssessmentRequest,
            DailyClimateData, ClimateTimeSeriesResponse, ClimateStatistics,
            ClimateCountrySummaryResponse, FireRiskAssessmentResponse, ClimateHealthCheckResponse,
            FireRiskLevel
        )
        return locals()[name]
    
    elif name in {
        # Analysis schemas
        "AnalysisType", "RegionType", "CorrelationMethod", "CorrelationRequest",
        "AnalysisListRequest", "StatisticalResults", "SpatialCellData", "CorrelationResponse",
        "AnalysisSummary", "AnalysisListResponse", "CorrelationMapResponse"
    }:
        from app.schemas.analysis import (
            AnalysisType, RegionType, CorrelationMethod, CorrelationRequest,
            AnalysisListRequest, StatisticalResults, SpatialCellData, CorrelationResponse,
            AnalysisSummary, AnalysisListResponse, CorrelationMapResponse
        )
        return locals()[name]
    
    raise AttributeError(f"module 'app.schemas' has no attribute '{name}'")


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