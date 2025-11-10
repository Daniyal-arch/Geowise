"""
GEOWISE - Analysis Schemas
app/schemas/analysis.py

Pydantic schemas for spatial correlation analysis.

These schemas validate requests for correlation analysis and format results.
Analysis results are cached in AnalysisResult model (see app/models/analysis.py).
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.schemas.common import BoundingBox, H3ResolutionEnum, GeoJSONFeatureCollection


# ============================================================================
# ENUMS
# ============================================================================

class AnalysisType(str, Enum):
    """Types of spatial correlation analysis supported by GEOWISE"""
    FIRE_TEMPERATURE = "fire_temperature"            # Fires vs temperature
    FIRE_DEFORESTATION = "fire_deforestation"        # Fires vs forest loss
    CLIMATE_FOREST = "climate_forest"                # Climate vs forest loss (yearly)
    FIRE_PRECIPITATION = "fire_precipitation"        # Fires vs rainfall
    FIRE_WIND = "fire_wind"                          # Fires vs wind speed
    MULTI_FACTOR = "multi_factor"                    # Multiple variables


class RegionType(str, Enum):
    """Region definition methods"""
    BBOX = "bbox"              # Bounding box
    COUNTRY = "country"        # Country ISO code
    H3_CELLS = "h3_cells"      # List of H3 hexagons
    CUSTOM = "custom"          # Custom GeoJSON polygon


class CorrelationMethod(str, Enum):
    """Statistical correlation methods"""
    PEARSON = "pearson"         # Linear correlation
    SPEARMAN = "spearman"       # Rank correlation
    KENDALL = "kendall"         # Tau correlation


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class CorrelationRequest(BaseModel):
    """
    Request spatial correlation analysis.
    
    Used by: POST /api/v1/analysis/correlate
    
    Example:
        {
            "analysis_type": "fire_temperature",
            "region_type": "country",
            "region_identifier": "PAK",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "h3_resolution": 5
        }
    """
    # Analysis definition
    analysis_type: AnalysisType = Field(..., description="Type of correlation to compute")
    analysis_name: Optional[str] = Field(None, description="Optional human-readable name")
    
    # Region definition (choose one)
    region_type: RegionType = Field(..., description="How region is defined")
    region_identifier: str = Field(..., description="Region identifier (ISO code, bbox string, etc.)")
    region_name: Optional[str] = Field(None, description="Optional human-readable region name")
    
    # For bbox region type
    bbox: Optional[BoundingBox] = Field(None, description="Bounding box (if region_type=bbox)")
    
    # Time period
    start_date: date = Field(..., description="Analysis start date")
    end_date: date = Field(..., description="Analysis end date")
    temporal_resolution: Optional[str] = Field(default="daily", description="daily, weekly, monthly")
    
    # Spatial resolution
    h3_resolution: int = Field(
        default=5, ge=0, le=15,
        description="H3 resolution for analysis (5=20km recommended for climate matching)"
    )
    
    # Analysis parameters
    correlation_method: CorrelationMethod = Field(default=CorrelationMethod.PEARSON)
    min_sample_size: int = Field(default=10, description="Minimum cells required for valid analysis")
    
    # Filters (optional)
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters (e.g., min_frp, confidence)")
    
    @validator('region_identifier')
    def validate_region_identifier(cls, v, values):
        """Validate region identifier based on region type"""
        region_type = values.get('region_type')
        
        if region_type == RegionType.COUNTRY:
            if len(v) != 3:
                raise ValueError('Country ISO code must be 3 letters')
            return v.upper()
        
        return v
    
    @validator('end_date')
    def end_after_start(cls, v, values):
        """Ensure end_date >= start_date"""
        start = values.get('start_date')
        if start and v < start:
            raise ValueError('end_date must be >= start_date')
        return v
    
    @root_validator
    def validate_bbox_for_bbox_region(cls, values):
        """If region_type is bbox, bbox must be provided"""
        region_type = values.get('region_type')
        bbox = values.get('bbox')
        
        if region_type == RegionType.BBOX and not bbox:
            raise ValueError('bbox must be provided when region_type is "bbox"')
        
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "analysis_type": "fire_temperature",
                "analysis_name": "Pakistan Fire-Temperature Correlation (Jan 2025)",
                "region_type": "country",
                "region_identifier": "PAK",
                "region_name": "Pakistan",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "temporal_resolution": "daily",
                "h3_resolution": 5,
                "correlation_method": "pearson",
                "min_sample_size": 10
            }
        }


class AnalysisListRequest(BaseModel):
    """
    Request list of cached analyses.
    
    Used by: GET /api/v1/analysis/list
    """
    analysis_type: Optional[AnalysisType] = Field(None, description="Filter by analysis type")
    region_identifier: Optional[str] = Field(None, description="Filter by region")
    is_significant: Optional[bool] = Field(None, description="Filter by statistical significance")
    
    # Pagination
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)
    
    # Sorting
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", description="asc or desc")
    
    class Config:
        schema_extra = {
            "example": {
                "analysis_type": "fire_temperature",
                "is_significant": True,
                "limit": 50
            }
        }


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class StatisticalResults(BaseModel):
    """
    Statistical measures from correlation analysis.
    """
    correlation_coefficient: float = Field(..., ge=-1, le=1, description="Pearson r (-1 to 1)")
    p_value: float = Field(..., ge=0, le=1, description="Statistical significance (p-value)")
    r_squared: Optional[float] = Field(None, ge=0, le=1, description="Coefficient of determination")
    
    sample_size: int = Field(..., description="Number of spatial cells analyzed")
    is_significant: bool = Field(..., description="True if p < 0.05")
    
    # Confidence interval (optional)
    confidence_interval_95: Optional[List[float]] = Field(
        None,
        description="95% confidence interval for correlation [lower, upper]"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "correlation_coefficient": 0.73,
                "p_value": 0.001,
                "r_squared": 0.53,
                "sample_size": 125,
                "is_significant": True,
                "confidence_interval_95": [0.65, 0.81]
            }
        }


class SpatialCellData(BaseModel):
    """
    Data for one spatial cell in the analysis.
    """
    h3_index: str = Field(..., description="H3 hexagon identifier")
    
    # Primary variable (e.g., fire count)
    primary_value: Optional[float] = Field(None, description="Value from primary dataset")
    
    # Secondary variable (e.g., temperature)
    secondary_value: Optional[float] = Field(None, description="Value from secondary dataset")
    
    # Statistical measures
    residual: Optional[float] = Field(None, description="Residual from regression line")
    local_correlation: Optional[float] = Field(None, description="Local correlation strength")
    
    class Config:
        schema_extra = {
            "example": {
                "h3_index": "851e2049fffffff",
                "primary_value": 12.0,
                "secondary_value": 29.8,
                "residual": 0.5,
                "local_correlation": 0.75
            }
        }


class CorrelationResponse(BaseModel):
    """
    Correlation analysis results.
    
    Response from: POST /api/v1/analysis/correlate
    """
    # Analysis metadata
    analysis_id: str = Field(..., description="Unique analysis ID (for caching)")
    analysis_type: str = Field(..., description="Type of analysis performed")
    analysis_name: Optional[str] = Field(None, description="Human-readable name")
    
    # Region info
    region: Dict[str, Any] = Field(..., description="Region definition")
    
    # Spatial resolution
    spatial_resolution: Dict[str, Any] = Field(..., description="H3 resolution info")
    
    # Datasets used
    datasets: List[str] = Field(..., description="Datasets involved in analysis")
    
    # Time period
    time_period: Dict[str, Any] = Field(..., description="Date range analyzed")
    
    # Statistical results
    statistics: StatisticalResults = Field(..., description="Correlation statistics")
    
    # Detailed results (optional - can be large)
    spatial_cells: Optional[List[SpatialCellData]] = Field(
        None,
        description="Per-cell data (omitted by default for large analyses)"
    )
    
    # Summary and interpretation
    summary: str = Field(..., description="Human-readable summary of findings")
    key_findings: List[str] = Field(default_factory=list, description="Key insights")
    
    # Visualization data (for frontend)
    visualization: Optional[Dict[str, Any]] = Field(None, description="Chart/map data")
    
    # Metadata
    metadata: Dict[str, Any] = Field(..., description="Computation metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "analysis_id": "abc123-def456",
                "analysis_type": "fire_temperature",
                "analysis_name": "Pakistan Fire-Temperature Correlation",
                "region": {
                    "type": "country",
                    "identifier": "PAK",
                    "name": "Pakistan"
                },
                "spatial_resolution": {
                    "h3_resolution": 5,
                    "cell_size": "~20km"
                },
                "datasets": ["fires", "climate"],
                "time_period": {
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                    "days": 31
                },
                "statistics": {
                    "correlation_coefficient": 0.73,
                    "p_value": 0.001,
                    "sample_size": 125,
                    "is_significant": True
                },
                "summary": "Strong positive correlation (r=0.73, p<0.001) between fire occurrence and temperature.",
                "key_findings": [
                    "73% correlation between fire density and temperature",
                    "Fires significantly more likely in areas above 30°C"
                ],
                "metadata": {
                    "computation_time": 7.5,
                    "cache_hit": False,
                    "created_at": "2025-01-15T10:30:00Z"
                }
            }
        }


class AnalysisSummary(BaseModel):
    """
    Summary of a cached analysis (without full results).
    
    Used in list endpoints.
    """
    analysis_id: str = Field(...)
    analysis_type: str = Field(...)
    analysis_name: Optional[str] = None
    
    region_identifier: str = Field(...)
    region_name: Optional[str] = None
    
    date_range: str = Field(..., description="e.g., '2025-01-01 to 2025-01-31'")
    
    correlation_coefficient: Optional[float] = None
    p_value: Optional[float] = None
    is_significant: bool = Field(...)
    
    created_at: datetime = Field(...)
    accessed_at: Optional[datetime] = None
    access_count: int = Field(default=0)
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "analysis_id": "abc123",
                "analysis_type": "fire_temperature",
                "analysis_name": "Pakistan Analysis",
                "region_identifier": "PAK",
                "region_name": "Pakistan",
                "date_range": "2025-01-01 to 2025-01-31",
                "correlation_coefficient": 0.73,
                "p_value": 0.001,
                "is_significant": True,
                "created_at": "2025-01-15T10:30:00Z",
                "access_count": 5
            }
        }


class AnalysisListResponse(BaseModel):
    """
    List of cached analyses.
    
    Response from: GET /api/v1/analysis/list
    """
    analyses: List[AnalysisSummary] = Field(..., description="List of analyses")
    total: int = Field(..., description="Total number of analyses matching filters")
    offset: int = Field(...)
    limit: int = Field(...)
    
    class Config:
        schema_extra = {
            "example": {
                "analyses": [],
                "total": 42,
                "offset": 0,
                "limit": 50
            }
        }


class CorrelationMapResponse(GeoJSONFeatureCollection):
    """
    Correlation results as GeoJSON for map visualization.
    
    Response from: GET /api/v1/analysis/{id}/map
    
    Each feature is an H3 hexagon with correlation data.
    """
    metadata: Dict[str, Any] = Field(..., description="Analysis metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "type": "FeatureCollection",
                "features": [],
                "metadata": {
                    "analysis_id": "abc123",
                    "correlation_coefficient": 0.73,
                    "h3_resolution": 5
                }
            }
        }


# Example usage
if __name__ == "__main__":
    """Test analysis schemas"""
    
    # Test CorrelationRequest
    request = CorrelationRequest(
        analysis_type=AnalysisType.FIRE_TEMPERATURE,
        region_type=RegionType.COUNTRY,
        region_identifier="PAK",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
        h3_resolution=5
    )
    print(f"✅ CorrelationRequest: {request.analysis_type} for {request.region_identifier}")
    
    # Test StatisticalResults
    stats = StatisticalResults(
        correlation_coefficient=0.73,
        p_value=0.001,
        r_squared=0.53,
        sample_size=125,
        is_significant=True
    )
    print(f"✅ StatisticalResults: r={stats.correlation_coefficient}, p={stats.p_value}, significant={stats.is_significant}")
    
    print("\n✅ Analysis schemas loaded successfully!")