"""
GEOWISE - Analysis Schemas (Pydantic V2)
app/schemas/analysis.py
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union, Literal  # ✅ Just this ONE line
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from enum import Enum

from app.schemas.common import BoundingBox, H3ResolutionEnum
class AnalysisType(str, Enum):
    """Types of spatial correlation analysis"""
    FIRE_TEMPERATURE = "fire_temperature"
    FIRE_DEFORESTATION = "fire_deforestation"
    CLIMATE_FOREST = "climate_forest"
    FIRE_PRECIPITATION = "fire_precipitation"
    FIRE_WIND = "fire_wind"
    MULTI_FACTOR = "multi_factor"


class RegionType(str, Enum):
    """Region definition methods"""
    BBOX = "bbox"
    COUNTRY = "country"
    H3_CELLS = "h3_cells"
    CUSTOM = "custom"


class CorrelationMethod(str, Enum):
    """Statistical correlation methods"""
    PEARSON = "pearson"
    SPEARMAN = "spearman"
    KENDALL = "kendall"


class CorrelationRequest(BaseModel):
    """Request spatial correlation analysis."""
    analysis_type: AnalysisType = Field(..., description="Type of correlation")
    analysis_name: Optional[str] = Field(None, description="Human-readable name")
    
    region_type: RegionType = Field(..., description="How region is defined")
    region_identifier: str = Field(..., description="Region identifier")
    region_name: Optional[str] = Field(None, description="Region name")
    
    bbox: Optional[BoundingBox] = Field(None, description="Bounding box if needed")
    
    start_date: date = Field(..., description="Analysis start date")
    end_date: date = Field(..., description="Analysis end date")
    temporal_resolution: Optional[str] = Field(default="daily", description="daily, weekly, monthly")
    
    h3_resolution: int = Field(default=5, ge=0, le=15, description="H3 resolution")
    
    correlation_method: CorrelationMethod = Field(default=CorrelationMethod.PEARSON)
    min_sample_size: int = Field(default=10, description="Minimum cells required")
    
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")
    
    @field_validator('region_identifier')
    @classmethod
    def validate_region_identifier(cls, v, info):
        """Validate region identifier based on region type"""
        region_type = info.data.get('region_type')
        
        if region_type == RegionType.COUNTRY:
            if len(v) != 3:
                raise ValueError('Country ISO code must be 3 letters')
            return v.upper()
        
        return v
    
    @field_validator('end_date')
    @classmethod
    def end_after_start(cls, v, info):
        """Ensure end_date >= start_date"""
        start = info.data.get('start_date')
        if start and v < start:
            raise ValueError('end_date must be >= start_date')
        return v
    
    @model_validator(mode='after')
    def validate_bbox_for_bbox_region(self):
        """If region_type is bbox, bbox must be provided"""
        if self.region_type == RegionType.BBOX and not self.bbox:
            raise ValueError('bbox must be provided when region_type is "bbox"')
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analysis_type": "fire_temperature",
                "region_type": "country",
                "region_identifier": "PAK",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "h3_resolution": 5,
                "correlation_method": "pearson"
            }
        }
    )


class AnalysisListRequest(BaseModel):
    """Request list of cached analyses."""
    analysis_type: Optional[AnalysisType] = Field(None, description="Filter by type")
    region_identifier: Optional[str] = Field(None, description="Filter by region")
    is_significant: Optional[bool] = Field(None, description="Filter by significance")
    
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)
    
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", description="asc or desc")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analysis_type": "fire_temperature",
                "is_significant": True,
                "limit": 50
            }
        }
    )


class StatisticalResults(BaseModel):
    """Statistical measures from correlation analysis."""
    correlation_coefficient: float = Field(..., ge=-1, le=1, description="Correlation coefficient")
    p_value: float = Field(..., ge=0, le=1, description="P-value")
    r_squared: Optional[float] = Field(None, ge=0, le=1, description="R-squared")
    
    sample_size: int = Field(..., description="Number of cells analyzed")
    is_significant: bool = Field(..., description="True if p < 0.05")
    
    confidence_interval_95: Optional[List[float]] = Field(None, description="95% CI [lower, upper]")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "correlation_coefficient": 0.73,
                "p_value": 0.001,
                "r_squared": 0.53,
                "sample_size": 125,
                "is_significant": True
            }
        }
    )


class SpatialCellData(BaseModel):
    """Data for one spatial cell in correlation analysis."""
    h3_index: str = Field(..., description="H3 hexagon identifier")
    centroid_lat: float = Field(..., description="Cell center latitude")
    centroid_lon: float = Field(..., description="Cell center longitude")
    
    variable_x: float = Field(..., description="First variable value")
    variable_y: float = Field(..., description="Second variable value")
    
    sample_count: Optional[int] = Field(None, description="Data points in this cell")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "h3_index": "851e2049fffffff",
                "centroid_lat": 30.5,
                "centroid_lon": 70.5,
                "variable_x": 320.5,
                "variable_y": 28.3,
                "sample_count": 12
            }
        }
    )


class CorrelationResponse(BaseModel):
    """Complete correlation analysis results."""
    analysis_id: str = Field(..., description="Unique analysis ID")
    
    analysis_type: str = Field(..., description="Type of analysis")
    analysis_name: Optional[str] = Field(None, description="Analysis name")
    
    region: Dict[str, Any] = Field(..., description="Region metadata")
    time_period: Dict[str, str] = Field(..., description="Date range")
    
    statistical_results: StatisticalResults = Field(..., description="Statistical measures")
    
    spatial_data: Optional[List[SpatialCellData]] = Field(None, description="Per-cell data")
    
    metadata: Dict[str, Any] = Field(..., description="Analysis metadata")
    
    created_at: datetime = Field(..., description="Analysis timestamp")
    cached: bool = Field(default=False, description="Retrieved from cache")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analysis_id": "abc123",
                "analysis_type": "fire_temperature",
                "region": {"type": "country", "identifier": "PAK"},
                "time_period": {"start": "2025-01-01", "end": "2025-01-31"},
                "statistical_results": {
                    "correlation_coefficient": 0.73,
                    "p_value": 0.001,
                    "sample_size": 125,
                    "is_significant": True
                },
                "metadata": {},
                "created_at": "2025-01-15T10:30:00Z",
                "cached": False
            }
        }
    )


class AnalysisSummary(BaseModel):
    """Summary of a cached analysis."""
    analysis_id: str = Field(..., description="Analysis ID")
    analysis_type: str = Field(..., description="Analysis type")
    region_identifier: str = Field(..., description="Region")
    
    correlation_coefficient: float = Field(..., description="Correlation")
    is_significant: bool = Field(..., description="Statistical significance")
    
    created_at: datetime = Field(..., description="Created timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analysis_id": "abc123",
                "analysis_type": "fire_temperature",
                "region_identifier": "PAK",
                "correlation_coefficient": 0.73,
                "is_significant": True,
                "created_at": "2025-01-15T10:30:00Z"
            }
        }
    )


class AnalysisListResponse(BaseModel):
    """List of cached analyses with pagination."""
    analyses: List[AnalysisSummary] = Field(..., description="Analysis summaries")
    
    total: int = Field(..., description="Total analyses matching filter")
    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Current limit")
    has_next: bool = Field(..., description="More results available")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analyses": [],
                "total": 42,
                "offset": 0,
                "limit": 50,
                "has_next": False
            }
        }
    )


# ✅ CORRECT - no recursion
class CorrelationMapResponse(BaseModel):
    """Correlation results as GeoJSON for mapping."""
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=lambda: {
        "analysis_type": "correlation",
        "source": "GEOWISE Analysis"
    })
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "FeatureCollection",
                "features": [],
                "metadata": {"analysis_type": "correlation"}
            }
        }
    )