"""
GEOWISE - Common Pydantic Schemas
app/schemas/common.py

Shared schemas used across multiple endpoints.
"""

from __future__ import annotations  # Enable forward references
from datetime import date, datetime
from typing import Optional, List, Any, Dict, Union, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum

# ============================================================================
# GEOGRAPHIC SCHEMAS
# ============================================================================

class BoundingBox(BaseModel):
    """Geographic bounding box for spatial queries."""
    min_lat: float = Field(..., ge=-90, le=90, description="Minimum latitude (South)")
    min_lon: float = Field(..., ge=-180, le=180, description="Minimum longitude (West)")
    max_lat: float = Field(..., ge=-90, le=90, description="Maximum latitude (North)")
    max_lon: float = Field(..., ge=-180, le=180, description="Maximum longitude (East)")
    
    @field_validator('max_lat')
    @classmethod
    def lat_max_greater_than_min(cls, v, info):
        if 'min_lat' in info.data and v <= info.data['min_lat']:
            raise ValueError('max_lat must be greater than min_lat')
        return v
    
    @field_validator('max_lon')
    @classmethod
    def lon_max_greater_than_min(cls, v, info):
        if 'min_lon' in info.data and v <= info.data['min_lon']:
            raise ValueError('max_lon must be greater than min_lon')
        return v
    
    def to_string(self) -> str:
        """Convert to NASA FIRMS format: west,south,east,north (lon,lat,lon,lat)"""
        return f"{self.min_lon},{self.min_lat},{self.max_lon},{self.max_lat}"
    
    @classmethod
    def from_string(cls, bbox_str: str) -> BoundingBox:
        """Parse NASA FIRMS format: west,south,east,north (lon,lat,lon,lat)"""
        coords = [float(x) for x in bbox_str.split(',')]
        if len(coords) != 4:
            raise ValueError("BBox string must have 4 values")
        return cls(min_lon=coords[0], min_lat=coords[1], max_lon=coords[2], max_lat=coords[3])
    
    def area_km2(self) -> float:
        lat_diff = self.max_lat - self.min_lat
        lon_diff = self.max_lon - self.min_lon
        return abs(lat_diff * lon_diff * 111 * 111)
    
    model_config = ConfigDict(json_schema_extra={"example": {"min_lat": 23.0, "min_lon": 60.0, "max_lat": 37.0, "max_lon": 77.5}})

class Point(BaseModel):
    """Single geographic point."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    
    model_config = ConfigDict(json_schema_extra={"example": {"latitude": 30.3753, "longitude": 69.3451}})


# ============================================================================
# TEMPORAL SCHEMAS
# ============================================================================

class DateRange(BaseModel):
    """Time period for temporal queries."""
    start_date: date = Field(...)
    end_date: date = Field(...)
    
    @field_validator('end_date')
    @classmethod
    def end_after_start(cls, v, info):
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('end_date must be on or after start_date')
        return v
    
    @field_validator('end_date')
    @classmethod
    def not_future(cls, v):
        if v > date.today():
            raise ValueError('end_date cannot be in the future')
        return v
    
    def days(self) -> int:
        return (self.end_date - self.start_date).days + 1
    
    model_config = ConfigDict(json_schema_extra={"example": {"start_date": "2025-01-01", "end_date": "2025-01-31"}})


# ============================================================================
# PAGINATION SCHEMAS
# ============================================================================

class PaginationParams(BaseModel):
    """Pagination parameters."""
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)
    
    model_config = ConfigDict(json_schema_extra={"example": {"offset": 0, "limit": 100}})


class PaginationMetadata(BaseModel):
    """Pagination metadata."""
    total: int = Field(...)
    offset: int = Field(...)
    limit: int = Field(...)
    has_next: bool = Field(...)
    has_prev: bool = Field(...)
    
    model_config = ConfigDict(json_schema_extra={"example": {"total": 3416, "offset": 0, "limit": 100, "has_next": True, "has_prev": False}})


# ============================================================================
# H3 SPATIAL SCHEMAS
# ============================================================================

class H3ResolutionEnum(int, Enum):
    """Valid H3 resolutions for GEOWISE."""
    ANALYSIS = 5
    REGIONAL = 6
    DISPLAY = 9
    NATIVE = 12


class H3Resolution(BaseModel):
    """H3 resolution with metadata."""
    resolution: int = Field(..., ge=0, le=15)
    cell_size_km: Optional[float] = Field(None)
    cell_count_estimate: Optional[int] = Field(None)
    
    @field_validator('resolution')
    @classmethod
    def validate_resolution(cls, v):
        return v
    
    @staticmethod
    def get_cell_size(resolution: int) -> float:
        sizes = {0: 4357.0, 1: 609.0, 2: 86.0, 3: 12.0, 4: 1.7, 5: 0.252, 6: 0.036, 7: 0.005, 8: 0.0007, 9: 0.000174, 10: 0.000015, 11: 0.000002, 12: 0.0000003, 13: 0.00000004, 14: 0.000000006, 15: 0.0000000009}
        return sizes.get(resolution, 0.0)
    
    model_config = ConfigDict(json_schema_extra={"example": {"resolution": 5, "cell_size_km": 0.252}})


# ============================================================================
# GEOJSON SCHEMAS (Simplified to avoid recursion)
# ============================================================================

class GeoJSONPoint(BaseModel):
    """GeoJSON Point geometry"""
    type: Literal["Point"] = "Point"
    coordinates: List[float] = Field(..., min_length=2, max_length=3)
    
    model_config = ConfigDict(json_schema_extra={"example": {"type": "Point", "coordinates": [69.3451, 30.3753]}})


class GeoJSONPolygon(BaseModel):
    """GeoJSON Polygon geometry"""
    type: Literal["Polygon"] = "Polygon"
    coordinates: List[List[List[float]]] = Field(...)
    
    model_config = ConfigDict(json_schema_extra={"example": {"type": "Polygon", "coordinates": [[[69.0, 30.0], [69.1, 30.0], [69.0, 30.0]]]}})


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature (geometry + properties)"""
    type: Literal["Feature"] = "Feature"
    geometry: Dict[str, Any] = Field(...)
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(json_schema_extra={"example": {"type": "Feature", "geometry": {"type": "Point", "coordinates": [69.3451, 30.3753]}, "properties": {"id": "abc123"}}})


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection (multiple features)"""
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: List[Dict[str, Any]] = Field(default_factory=list)  # Changed from List[GeoJSONFeature]
    metadata: Optional[Dict[str, Any]] = Field(None)
    
    model_config = ConfigDict(json_schema_extra={"example": {"type": "FeatureCollection", "features": [], "metadata": {"count": 0}}})


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class SuccessResponse(BaseModel):
    """Standard success response"""
    success: Literal[True] = True
    message: str = Field(...)
    data: Optional[Any] = Field(None)
    
    model_config = ConfigDict(json_schema_extra={"example": {"success": True, "message": "Success", "data": {}}})


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: Literal[False] = False
    error: Dict[str, Any] = Field(...)
    
    model_config = ConfigDict(json_schema_extra={"example": {"success": False, "error": {"code": "ERROR", "message": "Failed"}}})


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(...)
    service: str = Field(...)
    version: str = Field(...)
    timestamp: datetime = Field(default_factory=datetime.now)
    dependencies: Optional[Dict[str, str]] = Field(None)
    
    model_config = ConfigDict(json_schema_extra={"example": {"status": "healthy", "service": "GEOWISE", "version": "0.1.0", "timestamp": "2025-01-15T10:30:00Z"}})


# ============================================================================
# FILTER SCHEMAS
# ============================================================================

class SortOrder(str, Enum):
    """Sort order"""
    ASC = "asc"
    DESC = "desc"


class TemporalResolution(str, Enum):
    """Temporal resolution"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class ConfidenceLevel(str, Enum):
    """Fire confidence levels"""
    LOW = "l"
    NOMINAL = "n"
    HIGH = "h"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_country_iso(iso_code: str) -> str:
    """Validate 3-letter ISO country code."""
    if not iso_code or len(iso_code) != 3:
        raise ValueError("Country ISO code must be 3 letters")
    return iso_code.upper()