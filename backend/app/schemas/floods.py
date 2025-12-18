"""
GEOWISE - Flood Detection Schemas
==================================
app/schemas/floods.py

Pydantic schemas for SAR-based flood detection.
"""

from datetime import date
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class LocationTypeEnum(str, Enum):
    """Supported location types for flood detection"""
    COUNTRY = "country"
    PROVINCE = "province"
    STATE = "state"
    DISTRICT = "district"
    RIVER = "river"
    CITY = "city"
    PLACE = "place"
    BBOX = "bbox"
    POINT = "point"


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class FloodDetectionRequest(BaseModel):
    """
    Universal flood detection request.
    
    Supports multiple location specification methods:
    1. Named location (country, province, district, river, city)
    2. Bounding box coordinates
    3. Point coordinates with buffer
    
    Used by: POST /api/v1/floods/detect
    """
    
    # Location specification (provide ONE of these approaches)
    location_name: Optional[str] = Field(
        default=None, 
        description="Name of location (e.g., 'Sukkur', 'Sindh', 'Indus River', 'Pakistan')"
    )
    location_type: Optional[LocationTypeEnum] = Field(
        default=None,
        description="Type of location: country, province, district, river, city, bbox, point"
    )
    country: Optional[str] = Field(
        default=None,
        description="Country name for disambiguation (e.g., 'Pakistan', 'India')"
    )
    
    # For rivers, cities, or point-based queries
    buffer_km: Optional[float] = Field(
        default=None,
        ge=1,
        le=100,
        description="Buffer radius in km (for rivers: 20-30km, cities: 10-20km)"
    )
    
    # Direct coordinate specification
    bbox: Optional[List[float]] = Field(
        default=None,
        description="Bounding box [min_lon, min_lat, max_lon, max_lat]"
    )
    coordinates: Optional[List[float]] = Field(
        default=None,
        description="Point coordinates [longitude, latitude]"
    )
    
    # Temporal parameters (REQUIRED)
    before_start: date = Field(..., description="Pre-flood reference period start")
    before_end: date = Field(..., description="Pre-flood reference period end")
    after_start: date = Field(..., description="Flood detection period start")
    after_end: date = Field(..., description="Flood detection period end")
    
    # Detection parameters (optional)
    polarization: str = Field(default="VH", description="SAR polarization (VH or VV)")
    diff_threshold_db: float = Field(
        default=3.0, 
        ge=1.0, 
        le=10.0, 
        description="Change detection threshold in dB"
    )
    
    @field_validator('bbox')
    @classmethod
    def validate_bbox(cls, v):
        if v is None:
            return v
        if len(v) != 4:
            raise ValueError('bbox must have exactly 4 values')
        min_lon, min_lat, max_lon, max_lat = v
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise ValueError('Longitude must be between -180 and 180')
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError('Latitude must be between -90 and 90')
        if min_lon >= max_lon or min_lat >= max_lat:
            raise ValueError('Invalid bbox: min must be less than max')
        return v
    
    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v):
        if v is None:
            return v
        if len(v) != 2:
            raise ValueError('coordinates must have exactly 2 values [lon, lat]')
        lon, lat = v
        if not (-180 <= lon <= 180):
            raise ValueError('Longitude must be between -180 and 180')
        if not (-90 <= lat <= 90):
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @model_validator(mode='after')
    def validate_location(self):
        """Ensure at least one location method is provided"""
        has_name = self.location_name is not None
        has_bbox = self.bbox is not None
        has_coords = self.coordinates is not None
        
        if not (has_name or has_bbox or has_coords):
            raise ValueError(
                'Must provide location_name, bbox, or coordinates'
            )
        return self
    
    @model_validator(mode='after')
    def validate_dates(self):
        """Validate date ranges"""
        if self.before_end < self.before_start:
            raise ValueError('before_end must be after before_start')
        if self.after_end < self.after_start:
            raise ValueError('after_end must be after after_start')
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location_name": "Sukkur",
                "location_type": "district",
                "country": "Pakistan",
                "before_start": "2022-06-01",
                "before_end": "2022-07-15",
                "after_start": "2022-08-25",
                "after_end": "2022-09-05"
            }
        }
    )


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class FloodLocationInfo(BaseModel):
    """Location information in response"""
    name: Optional[str] = Field(default=None, description="Location name")
    type: Optional[str] = Field(default=None, description="Location type")
    country: Optional[str] = Field(default=None, description="Country name")
    province: Optional[str] = Field(default=None, description="Province/State name")
    district: Optional[str] = Field(default=None, description="District name")
    admin_level: Optional[int] = Field(default=None, description="Admin level (0=country, 1=province, 2=district)")
    buffer_km: Optional[float] = Field(default=None, description="Buffer radius if applicable")
    
    model_config = ConfigDict(extra='allow')


class FloodStatistics(BaseModel):
    """Flood extent and impact statistics"""
    area_km2: float = Field(default=0, description="Flood extent in square kilometers")
    area_ha: float = Field(default=0, description="Flood extent in hectares")
    exposed_population: int = Field(default=0, description="Estimated exposed population")
    flooded_cropland_ha: float = Field(default=0, description="Flooded agricultural land in hectares")
    flooded_urban_ha: float = Field(default=0, description="Flooded urban area in hectares")
    
    model_config = ConfigDict(extra='allow')


class FloodTiles(BaseModel):
    """Tile URLs for map visualization"""
    flood_extent: Optional[str] = Field(default=None, description="Flood extent layer (red)")
    change_detection: Optional[str] = Field(default=None, description="SAR change detection layer")
    sar_before: Optional[str] = Field(default=None, description="Pre-flood SAR imagery")
    sar_after: Optional[str] = Field(default=None, description="Post-flood SAR imagery")
    permanent_water: Optional[str] = Field(default=None, description="Permanent water mask (cyan)")
    
    model_config = ConfigDict(extra='allow')


class FloodDateRange(BaseModel):
    """Date range"""
    start: str
    end: str


class FloodDates(BaseModel):
    """Before and after date ranges"""
    before: FloodDateRange
    after: FloodDateRange


class FloodImagesUsed(BaseModel):
    """Sentinel-1 images used"""
    before: int = Field(default=0)
    after: int = Field(default=0)


class FloodConfig(BaseModel):
    """Detection configuration"""
    polarization: str = Field(default="VH")
    threshold_db: float = Field(default=3.0)
    min_cluster_pixels: Optional[int] = Field(default=None)
    
    model_config = ConfigDict(extra='allow')


class FloodDetectionResponse(BaseModel):
    """
    Flood detection result.
    
    Returned by: POST /api/v1/floods/detect
    """
    success: bool = Field(..., description="Whether detection succeeded")
    
    # Error info (if failed)
    error: Optional[str] = Field(default=None, description="Error message if failed")
    suggestion: Optional[str] = Field(default=None, description="Suggestion for fixing the issue")
    
    # Location info
    location: Optional[Union[FloodLocationInfo, Dict[str, Any]]] = Field(default=None, description="Resolved location info")
    
    # Map positioning
    center: Optional[List[float]] = Field(default=None, description="Map center [lon, lat]")
    zoom: Optional[int] = Field(default=None, description="Recommended zoom level")
    
    # Results
    dates: Optional[Union[FloodDates, Dict[str, Any]]] = Field(default=None, description="Date ranges used")
    statistics: Optional[Union[FloodStatistics, Dict[str, Any]]] = Field(default=None, description="Flood statistics")
    tiles: Optional[Union[FloodTiles, Dict[str, Any]]] = Field(default=None, description="Tile URLs for visualization")
    
    # Metadata
    images_used: Optional[Union[FloodImagesUsed, Dict[str, Any]]] = Field(default=None, description="Sentinel-1 images used")
    config: Optional[Union[FloodConfig, Dict[str, Any]]] = Field(default=None, description="Detection configuration")
    generated_at: Optional[str] = Field(default=None, description="Timestamp of generation")
    
    model_config = ConfigDict(
        extra='allow',
        json_schema_extra={
            "example": {
                "success": True,
                "location": {
                    "name": "Sukkur",
                    "type": "district",
                    "country": "Pakistan",
                    "province": "Sindh",
                    "admin_level": 2
                },
                "center": [68.86, 27.70],
                "zoom": 9,
                "dates": {
                    "before": {"start": "2022-06-01", "end": "2022-07-15"},
                    "after": {"start": "2022-08-25", "end": "2022-09-05"}
                },
                "statistics": {
                    "area_km2": 1250.5,
                    "area_ha": 125050.0,
                    "exposed_population": 350000,
                    "flooded_cropland_ha": 85000.0,
                    "flooded_urban_ha": 2500.0
                },
                "tiles": {
                    "flood_extent": "https://earthengine.googleapis.com/...",
                    "change_detection": "https://earthengine.googleapis.com/..."
                },
                "images_used": {"before": 23, "after": 6},
                "config": {"polarization": "VH", "threshold_db": 3.0},
                "generated_at": "2025-01-15T12:00:00Z"
            }
        }
    )


# ============================================================================
# UTILITY SCHEMAS
# ============================================================================

class AdminLevelsResponse(BaseModel):
    """List of admin divisions for a country"""
    country: str
    provinces: List[str] = Field(default_factory=list)
    district_count: int = Field(default=0)
    note: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)
    
    model_config = ConfigDict(extra='allow')


class DistrictListResponse(BaseModel):
    """List of districts for a province"""
    country: str
    province: str
    districts: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(extra='allow')


class FloodExamplesResponse(BaseModel):
    """Example flood queries"""
    description: str
    examples: Dict[str, Any]
    natural_language_queries: List[str]
    methodology: Dict[str, Any]
    
    model_config = ConfigDict(extra='allow')


class HealthResponse(BaseModel):
    """Service health check"""
    status: str
    gee_initialized: bool
    sentinel1_available: bool
    message: Optional[str] = Field(default=None)
    
    model_config = ConfigDict(extra='allow')