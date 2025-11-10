"""
GEOWISE - Common Pydantic Schemas
app/schemas/common.py

Shared schemas used across multiple endpoints.

WHY PYDANTIC SCHEMAS:
- Automatic request validation (FastAPI checks before your code runs)
- Type safety (catches errors at API boundary)
- Auto-generated documentation (Swagger/OpenAPI)
- Serialization (SQLAlchemy models → JSON responses)

WHAT'S IN THIS FILE:
- BoundingBox: Geographic area definition
- DateRange: Time period with validation
- Pagination: Offset/limit for large result sets
- H3Resolution: Valid H3 resolution levels
- GeoJSON: Standard geographic response format
"""

from datetime import date, datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum


# ============================================================================
# GEOGRAPHIC SCHEMAS
# ============================================================================

class BoundingBox(BaseModel):
    """
    Geographic bounding box for spatial queries.
    
    Used to define a rectangular area on Earth's surface.
    
    Example:
        Pakistan bbox: {"lat_min": 23.0, "lon_min": 60.0, 
                       "lat_max": 37.0, "lon_max": 77.5}
    
    WHY VALIDATION:
    - Latitude must be -90 to 90 (North/South poles)
    - Longitude must be -180 to 180 (International Date Line)
    - Max must be greater than Min
    """
    lat_min: float = Field(..., ge=-90, le=90, description="Minimum latitude (South)")
    lon_min: float = Field(..., ge=-180, le=180, description="Minimum longitude (West)")
    lat_max: float = Field(..., ge=-90, le=90, description="Maximum latitude (North)")
    lon_max: float = Field(..., ge=-180, le=180, description="Maximum longitude (East)")
    
    @validator('lat_max')
    def lat_max_greater_than_min(cls, v, values):
        """Ensure lat_max > lat_min"""
        if 'lat_min' in values and v <= values['lat_min']:
            raise ValueError('lat_max must be greater than lat_min')
        return v
    
    @validator('lon_max')
    def lon_max_greater_than_min(cls, v, values):
        """Ensure lon_max > lon_min"""
        if 'lon_min' in values and v <= values['lon_min']:
            raise ValueError('lon_max must be greater than lon_min')
        return v
    
    def to_string(self) -> str:
        """Convert to comma-separated string: 'lat_min,lon_min,lat_max,lon_max'"""
        return f"{self.lat_min},{self.lon_min},{self.lat_max},{self.lon_max}"
    
    @classmethod
    def from_string(cls, bbox_str: str) -> 'BoundingBox':
        """Parse from comma-separated string"""
        coords = [float(x) for x in bbox_str.split(',')]
        if len(coords) != 4:
            raise ValueError("BBox string must have 4 values: lat_min,lon_min,lat_max,lon_max")
        return cls(lat_min=coords[0], lon_min=coords[1], lat_max=coords[2], lon_max=coords[3])
    
    def area_km2(self) -> float:
        """Approximate area in square kilometers (rough estimate)"""
        lat_diff = self.lat_max - self.lat_min
        lon_diff = self.lon_max - self.lon_min
        # Rough approximation: 1 degree ≈ 111 km
        return abs(lat_diff * lon_diff * 111 * 111)
    
    class Config:
        schema_extra = {
            "example": {
                "lat_min": 23.0,
                "lon_min": 60.0,
                "lat_max": 37.0,
                "lon_max": 77.5
            }
        }


class Point(BaseModel):
    """
    Single geographic point.
    
    Used for location queries (e.g., "climate at this point").
    """
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    
    class Config:
        schema_extra = {
            "example": {
                "latitude": 30.3753,
                "longitude": 69.3451
            }
        }


# ============================================================================
# TEMPORAL SCHEMAS
# ============================================================================

class DateRange(BaseModel):
    """
    Time period for temporal queries.
    
    WHY VALIDATION:
    - end_date must be after start_date
    - Can't query future dates (data doesn't exist yet)
    - NASA FIRMS only has last 10 days (will validate in service layer)
    """
    start_date: date = Field(..., description="Start date (inclusive)")
    end_date: date = Field(..., description="End date (inclusive)")
    
    @validator('end_date')
    def end_after_start(cls, v, values):
        """Ensure end_date >= start_date"""
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('end_date must be on or after start_date')
        return v
    
    @validator('end_date')
    def not_future(cls, v):
        """Prevent querying future dates"""
        if v > date.today():
            raise ValueError('end_date cannot be in the future')
        return v
    
    def days(self) -> int:
        """Calculate number of days in range"""
        return (self.end_date - self.start_date).days + 1
    
    class Config:
        schema_extra = {
            "example": {
                "start_date": "2025-01-01",
                "end_date": "2025-01-31"
            }
        }


# ============================================================================
# PAGINATION SCHEMAS
# ============================================================================

class PaginationParams(BaseModel):
    """
    Pagination parameters for large result sets.
    
    Standard offset/limit pagination.
    
    Example:
        Page 1: offset=0, limit=100 (items 1-100)
        Page 2: offset=100, limit=100 (items 101-200)
    """
    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum items to return")
    
    class Config:
        schema_extra = {
            "example": {
                "offset": 0,
                "limit": 100
            }
        }


class PaginationMetadata(BaseModel):
    """
    Pagination metadata for API responses.
    
    Helps frontend build pagination UI.
    """
    total: int = Field(..., description="Total number of items")
    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Current limit")
    has_next: bool = Field(..., description="Whether more items exist")
    has_prev: bool = Field(..., description="Whether previous items exist")
    
    class Config:
        schema_extra = {
            "example": {
                "total": 3416,
                "offset": 0,
                "limit": 100,
                "has_next": True,
                "has_prev": False
            }
        }


# ============================================================================
# H3 SPATIAL SCHEMAS
# ============================================================================

class H3ResolutionEnum(int, Enum):
    """
    Valid H3 resolutions for GEOWISE.
    
    We only support specific resolutions that make sense:
    - Resolution 5: ~20km (analysis - matches climate)
    - Resolution 6: ~3km (regional aggregation)
    - Resolution 9: ~174m (display - 1km visualization)
    - Resolution 12: ~2.8m (native fire resolution - storage only)
    """
    ANALYSIS = 5      # 20km cells for statistical correlation
    REGIONAL = 6      # 3km cells for province/state aggregation
    DISPLAY = 9       # 174m cells for map visualization
    NATIVE = 12       # 2.8m cells for exact fire locations


class H3Resolution(BaseModel):
    """
    H3 resolution with metadata.
    
    Provides cell size information for users.
    """
    resolution: int = Field(..., ge=0, le=15, description="H3 resolution level")
    cell_size_km: Optional[float] = Field(None, description="Approximate cell size in km")
    cell_count_estimate: Optional[int] = Field(None, description="Estimated cells in query area")
    
    @validator('resolution')
    def validate_resolution(cls, v):
        """Warn if using uncommon resolution"""
        valid_resolutions = [5, 6, 9, 12]
        if v not in valid_resolutions:
            # Allow it, but it's unusual
            pass
        return v
    
    @staticmethod
    def get_cell_size(resolution: int) -> float:
        """Get approximate cell size in km for a resolution"""
        sizes = {
            0: 4357.0,
            1: 609.0,
            2: 86.0,
            3: 12.0,
            4: 1.7,
            5: 0.252,  # 252 meters
            6: 0.036,  # 36 meters
            7: 0.005,  # 5 meters
            8: 0.0007,
            9: 0.000174,  # 174 meters (displayed as 0.174 km)
            10: 0.000015,
            11: 0.000002,
            12: 0.0000003,
            13: 0.00000004,
            14: 0.000000006,
            15: 0.0000000009
        }
        return sizes.get(resolution, 0.0)
    
    class Config:
        schema_extra = {
            "example": {
                "resolution": 5,
                "cell_size_km": 0.252,
                "cell_count_estimate": 125
            }
        }


# ============================================================================
# GEOJSON SCHEMAS
# ============================================================================

class GeoJSONPoint(BaseModel):
    """GeoJSON Point geometry"""
    type: str = Field(default="Point", const=True)
    coordinates: List[float] = Field(..., min_items=2, max_items=3)
    
    class Config:
        schema_extra = {
            "example": {
                "type": "Point",
                "coordinates": [69.3451, 30.3753]  # [longitude, latitude]
            }
        }


class GeoJSONPolygon(BaseModel):
    """GeoJSON Polygon geometry (for H3 hexagons)"""
    type: str = Field(default="Polygon", const=True)
    coordinates: List[List[List[float]]] = Field(...)
    
    class Config:
        schema_extra = {
            "example": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [69.0, 30.0],
                        [69.1, 30.0],
                        [69.15, 30.05],
                        [69.1, 30.1],
                        [69.0, 30.1],
                        [68.95, 30.05],
                        [69.0, 30.0]  # Close the ring
                    ]
                ]
            }
        }


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature (geometry + properties)"""
    type: str = Field(default="Feature", const=True)
    geometry: Dict[str, Any] = Field(...)
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [69.3451, 30.3753]
                },
                "properties": {
                    "id": "abc123",
                    "name": "Fire Detection",
                    "frp": 12.5
                }
            }
        }


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection (multiple features)"""
    type: str = Field(default="FeatureCollection", const=True)
    features: List[GeoJSONFeature] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "type": "FeatureCollection",
                "features": [],
                "metadata": {
                    "count": 0,
                    "source": "GEOWISE API"
                }
            }
        }


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class SuccessResponse(BaseModel):
    """Standard success response wrapper"""
    success: bool = Field(default=True, const=True)
    message: str = Field(..., description="Success message")
    data: Optional[Any] = Field(None, description="Response data")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"id": "abc123"}
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response wrapper"""
    success: bool = Field(default=False, const=True)
    error: Dict[str, Any] = Field(..., description="Error details")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input parameters",
                    "details": {}
                }
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check endpoint response"""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.now)
    dependencies: Optional[Dict[str, str]] = Field(None, description="Dependency health status")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "service": "GEOWISE API",
                "version": "0.1.0",
                "timestamp": "2025-01-15T10:30:00Z",
                "dependencies": {
                    "database": "healthy",
                    "redis": "healthy"
                }
            }
        }


# ============================================================================
# FILTER SCHEMAS
# ============================================================================

class SortOrder(str, Enum):
    """Sort order for list endpoints"""
    ASC = "asc"
    DESC = "desc"


class TemporalResolution(str, Enum):
    """Temporal aggregation resolution"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class ConfidenceLevel(str, Enum):
    """Fire detection confidence levels (NASA FIRMS)"""
    LOW = "l"
    NOMINAL = "n"
    HIGH = "h"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_country_iso(iso_code: str) -> str:
    """
    Validate 3-letter ISO country code.
    
    For MVP, we just check length and format.
    In production, validate against ISO 3166-1 alpha-3 list.
    """
    if not iso_code or len(iso_code) != 3:
        raise ValueError("Country ISO code must be 3 letters (e.g., 'PAK', 'IND', 'USA')")
    
    return iso_code.upper()


# Example usage
if __name__ == "__main__":
    """Test common schemas"""
    
    # Test BoundingBox
    bbox = BoundingBox(lat_min=23.0, lon_min=60.0, lat_max=37.0, lon_max=77.5)
    print(f"✅ BBox: {bbox.to_string()}")
    print(f"   Area: ~{bbox.area_km2():,.0f} km²")
    
    # Test DateRange
    date_range = DateRange(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))
    print(f"✅ DateRange: {date_range.days()} days")
    
    # Test H3 Resolution
    res = H3Resolution(resolution=5, cell_size_km=H3Resolution.get_cell_size(5))
    print(f"✅ H3 Resolution {res.resolution}: ~{res.cell_size_km} km per cell")
    
    print("\n✅ Common schemas loaded successfully!")