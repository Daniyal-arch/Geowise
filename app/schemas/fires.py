"""
GEOWISE - Fire Data Schemas
app/schemas/fires.py

Pydantic schemas for NASA FIRMS fire detection data.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

# Import only what we need directly, avoid circular imports
from app.schemas.common import (
    BoundingBox, PaginationMetadata,
    H3ResolutionEnum, ConfidenceLevel, SortOrder
)


# ============================================================================
# REQUEST SCHEMAS (Input Validation)
# ============================================================================

class FireQueryRequest(BaseModel):
    """
    Query fires by geographic area and time period.
    
    Used by: GET /api/v1/fires
    """
    # Spatial filter (choose one)
    bbox: Optional[BoundingBox] = Field(None, description="Bounding box for spatial query")
    country_iso: Optional[str] = Field(None, min_length=3, max_length=3, 
                                       description="3-letter country code (e.g., 'PAK')")
    
    # Temporal filter
    start_date: Optional[date] = Field(None, description="Start date (inclusive)")
    end_date: Optional[date] = Field(None, description="End date (inclusive)")
    days: Optional[int] = Field(None, ge=1, le=10, 
                               description="Number of days back from today (NASA FIRMS limit: 10)")
    
    # Fire intensity filters
    min_frp: Optional[float] = Field(None, ge=0, description="Minimum Fire Radiative Power (MW)")
    max_frp: Optional[float] = Field(None, description="Maximum Fire Radiative Power (MW)")
    min_brightness: Optional[float] = Field(None, description="Minimum brightness temperature (K)")
    confidence: Optional[ConfidenceLevel] = Field(None, description="Minimum confidence level")
    
    # Satellite filter
    satellite: Optional[str] = Field(None, description="Satellite name (e.g., 'N' for NOAA-20)")
    
    # Pagination
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=10000)
    
    # Sorting
    sort_by: Optional[str] = Field(default="acq_date", description="Field to sort by")
    sort_order: Optional[SortOrder] = Field(default=SortOrder.DESC)
    
    @field_validator('country_iso')
    @classmethod
    def uppercase_country(cls, v):
        """Convert country code to uppercase"""
        return v.upper() if v else None
    
    @model_validator(mode='after')
    def validate_spatial_filter(self):
        """Must provide either bbox OR country_iso"""
        if not self.bbox and not self.country_iso:
            raise ValueError('Must provide either bbox or country_iso')
        
        if self.bbox and self.country_iso:
            raise ValueError('Provide only one: bbox or country_iso')
        
        return self
    
    @model_validator(mode='after')
    def validate_temporal_filter(self):
        """Must provide either (start_date + end_date) OR days"""
        if self.days:
            # Using 'days' - ignore start/end dates
            if self.start_date or self.end_date:
                raise ValueError('When using "days", do not provide start_date or end_date')
        else:
            # Using date range - both required
            if not self.start_date or not self.end_date:
                raise ValueError('Must provide both start_date and end_date, or use "days"')
            
            if self.end_date < self.start_date:
                raise ValueError('end_date must be after start_date')
            
            # Check if date range exceeds 10 days
            days_diff = (self.end_date - self.start_date).days + 1
            if days_diff > 10:
                raise ValueError('NASA FIRMS data limited to 10 days. Use smaller date range.')
        
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "country_iso": "PAK",
                "days": 7,
                "min_frp": 10.0,
                "confidence": "h",
                "limit": 100
            }
        }
    )


class FireAggregationRequest(BaseModel):
    """Request aggregated fire statistics at H3 resolution."""
    bbox: Optional[BoundingBox] = Field(None)
    country_iso: Optional[str] = Field(None, min_length=3, max_length=3)
    
    # Time period
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: Optional[int] = Field(None, ge=1, le=10)
    
    # H3 resolution for aggregation
    resolution: H3ResolutionEnum = Field(
        default=H3ResolutionEnum.DISPLAY,
        description="H3 resolution (5=20km analysis, 9=174m display)"
    )
    
    # Return format
    format: str = Field(default="geojson", description="Response format: 'geojson' or 'json'")
    
    @model_validator(mode='after')
    def validate_filters(self):
        """Same validations as FireQueryRequest"""
        # Check spatial filter
        if not self.bbox and not self.country_iso:
            raise ValueError('Must provide either bbox or country_iso')
        if self.bbox and self.country_iso:
            raise ValueError('Provide only one: bbox or country_iso')
        
        # Check temporal filter
        if not self.days and not (self.start_date and self.end_date):
            raise ValueError('Must provide date range or days')
        
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "country_iso": "PAK",
                "days": 7,
                "resolution": 9,
                "format": "geojson"
            }
        }
    )


# ============================================================================
# BASE FIRE DETECTION MODEL (No dependencies)
# ============================================================================

class FireDetectionBase(BaseModel):
    """Base fire detection fields without circular dependencies."""
    id: str = Field(..., description="Unique fire detection ID")
    latitude: float = Field(..., description="Latitude in decimal degrees")
    longitude: float = Field(..., description="Longitude in decimal degrees")
    h3_index_9: str = Field(..., description="H3 index at resolution 9 (174m)")
    brightness: float = Field(..., description="Brightness temperature (Kelvin)")
    confidence: str = Field(..., description="Confidence level")
    satellite: str = Field(..., description="Satellite identifier")
    acq_date: datetime = Field(..., description="Acquisition date/time (UTC)")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# RESPONSE SCHEMAS (Output Formatting)
# ============================================================================

class FireDetectionResponse(FireDetectionBase):
    """Single fire detection record."""
    h3_index_5: Optional[str] = Field(None, description="H3 index at resolution 5 (20km)")
    bright_ti5: Optional[float] = Field(None, description="Brightness temperature I-5")
    frp: Optional[float] = Field(None, description="Fire Radiative Power (MW)")
    instrument: Optional[str] = Field(None, description="Instrument name")
    acq_time: Optional[str] = Field(None, description="Acquisition time (HHMM)")
    daynight: Optional[str] = Field(None, description="'D' (day) or 'N' (night)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "abc123-def456",
                "latitude": 30.5128,
                "longitude": 70.3456,
                "h3_index_9": "891e204a57fffff",
                "h3_index_5": "851e2049fffffff",
                "brightness": 320.5,
                "frp": 12.5,
                "confidence": "h",
                "satellite": "N",
                "instrument": "VIIRS",
                "acq_date": "2025-01-15T10:30:00Z",
                "daynight": "D"
            }
        }
    )


class FireListResponse(BaseModel):
    """Paginated list of fire detections."""
    fires: List[FireDetectionResponse] = Field(..., description="List of fire detections")
    pagination: PaginationMetadata = Field(..., description="Pagination info")
    summary: Optional[Dict[str, Any]] = Field(None, description="Summary statistics")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fires": [],
                "pagination": {
                    "total": 3416,
                    "offset": 0,
                    "limit": 100,
                    "has_next": True,
                    "has_prev": False
                },
                "summary": {
                    "total_fires": 3416,
                    "avg_frp": 12.3,
                    "high_confidence_count": 2890
                }
            }
        }
    )


class FireAggregationCell(BaseModel):
    """Aggregated fire statistics for one H3 hexagon."""
    h3_index: str = Field(..., description="H3 hexagon identifier")
    resolution: int = Field(..., description="H3 resolution level")
    
    # Fire statistics
    fire_count: int = Field(..., description="Number of fires in this cell")
    total_frp: Optional[float] = Field(None, description="Sum of FRP")
    avg_frp: Optional[float] = Field(None, description="Average FRP")
    max_frp: Optional[float] = Field(None, description="Maximum FRP")
    
    # Confidence breakdown
    high_confidence_count: int = Field(default=0)
    nominal_confidence_count: int = Field(default=0)
    low_confidence_count: int = Field(default=0)
    
    # Centroid
    centroid_lat: Optional[float] = Field(None, description="Cell center latitude")
    centroid_lon: Optional[float] = Field(None, description="Cell center longitude")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "h3_index": "851e2049fffffff",
                "resolution": 5,
                "fire_count": 12,
                "total_frp": 156.8,
                "avg_frp": 13.1,
                "max_frp": 25.4,
                "high_confidence_count": 10,
                "nominal_confidence_count": 2,
                "low_confidence_count": 0,
                "centroid_lat": 30.5,
                "centroid_lon": 70.5
            }
        }
    )


class FireAggregationResponse(BaseModel):
    """Aggregated fire data at H3 resolution."""
    cells: List[FireAggregationCell] = Field(..., description="Aggregated H3 cells")
    metadata: Dict[str, Any] = Field(..., description="Query metadata")
    summary: Dict[str, Any] = Field(..., description="Overall statistics")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cells": [],
                "metadata": {
                    "resolution": 5,
                    "date_range": "2025-01-01 to 2025-01-10",
                    "region": "PAK"
                },
                "summary": {
                    "total_fires": 3416,
                    "cells_with_fires": 125,
                    "avg_fires_per_cell": 27.3
                }
            }
        }
    )


class FireStatisticsResponse(BaseModel):
    """Overall fire statistics for a region/time period."""
    total_fires: int = Field(..., description="Total fire count")
    date_range: Dict[str, str] = Field(..., description="Date range analyzed")
    region: str = Field(..., description="Region identifier")
    
    frp_statistics: Dict[str, float] = Field(..., description="FRP stats")
    brightness_statistics: Dict[str, float] = Field(..., description="Brightness stats")
    confidence_distribution: Dict[str, int] = Field(..., description="Count by confidence level")
    fires_by_date: List[Dict[str, Any]] = Field(..., description="Daily fire counts")
    fires_by_h3: List[Dict[str, Any]] = Field(..., description="Fire counts by H3 cell")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_fires": 3416,
                "date_range": {"start": "2025-01-01", "end": "2025-01-10"},
                "region": "PAK",
                "frp_statistics": {"min": 2.1, "max": 45.7, "avg": 12.3, "total": 42028.8},
                "confidence_distribution": {"high": 2890, "nominal": 450, "low": 76}
            }
        }
    )


class FireGeoJSONResponse(BaseModel):
    """Fire data in GeoJSON format for mapping."""
    metadata: Dict[str, Any] = Field(default_factory=lambda: {
        "source": "NASA FIRMS",
        "dataset": "VIIRS_SNPP_NRT",
        "resolution": "375m"
    })
    
    # GeoJSON structure
    type: str = Field(default="FeatureCollection")
    features: List[Dict[str, Any]] = Field(default_factory=list, description="GeoJSON features")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "FeatureCollection",
                "metadata": {
                    "source": "NASA FIRMS",
                    "dataset": "VIIRS_SNPP_NRT",
                    "resolution": "375m",
                    "total_features": 150
                },
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [70.3456, 30.5128]
                        },
                        "properties": {
                            "id": "abc123-def456",
                            "brightness": 320.5,
                            "frp": 12.5,
                            "confidence": "h",
                            "acq_date": "2025-01-15T10:30:00Z"
                        }
                    }
                ]
            }
        }
    )


class FireAlertResponse(BaseModel):
    """Fire alert notification format."""
    alert_id: str = Field(..., description="Unique alert identifier")
    alert_type: str = Field(..., description="Alert type (e.g., 'new_fire', 'high_intensity')")
    severity: str = Field(..., description="Alert severity level")
    timestamp: datetime = Field(..., description="Alert generation time")
    
    # Fire details - use the base model to avoid recursion
    fire_data: FireDetectionBase = Field(..., description="Fire detection details")
    
    # Location context
    location_context: Dict[str, Any] = Field(..., description="Location context (country, region, etc.)")
    
    # Alert metadata
    triggered_by: Dict[str, Any] = Field(..., description="What triggered this alert")
    recommendations: List[str] = Field(..., description="Recommended actions")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "alert_id": "alert_20250115_12345",
                "alert_type": "high_intensity_fire",
                "severity": "high",
                "timestamp": "2025-01-15T10:35:00Z",
                "fire_data": {
                    "id": "abc123-def456",
                    "latitude": 30.5128,
                    "longitude": 70.3456,
                    "brightness": 420.5,
                    "frp": 45.2,
                    "confidence": "h"
                },
                "location_context": {
                    "country": "Pakistan",
                    "region": "Punjab",
                    "population_density": "medium",
                    "protected_area": False
                },
                "triggered_by": {
                    "frp_threshold": 40.0,
                    "brightness_threshold": 400.0
                },
                "recommendations": [
                    "Dispatch fire response team",
                    "Issue public health advisory",
                    "Monitor wind direction changes"
                ]
            }
        }
    )


class FireTrendResponse(BaseModel):
    """Fire trend analysis over time."""
    period: Dict[str, str] = Field(..., description="Analysis period")
    region: str = Field(..., description="Region analyzed")
    
    # Trend metrics
    total_fires: int = Field(..., description="Total fires in period")
    trend_direction: str = Field(..., description="'increasing', 'decreasing', 'stable'")
    trend_percentage: float = Field(..., description="Percentage change from previous period")
    
    # Daily breakdown
    daily_totals: List[Dict[str, Any]] = Field(..., description="Fires by day")
    
    # Hotspot analysis
    hotspots: List[Dict[str, Any]] = Field(..., description="Areas with highest fire density")
    
    # Comparative analysis
    comparison_to_previous: Dict[str, Any] = Field(..., description="Comparison to previous period")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period": {
                    "start": "2025-01-01",
                    "end": "2025-01-10"
                },
                "region": "PAK",
                "total_fires": 3416,
                "trend_direction": "increasing",
                "trend_percentage": 15.7,
                "daily_totals": [
                    {"date": "2025-01-01", "count": 285},
                    {"date": "2025-01-02", "count": 312}
                ],
                "hotspots": [
                    {
                        "h3_index": "851e2049fffffff",
                        "fire_count": 45,
                        "region_name": "Central Punjab"
                    }
                ],
                "comparison_to_previous": {
                    "previous_period_fires": 2952,
                    "change_percentage": 15.7,
                    "notable_changes": [
                        "Increased activity in Punjab region",
                        "Decreased activity in northern areas"
                    ]
                }
            }
        }
    )