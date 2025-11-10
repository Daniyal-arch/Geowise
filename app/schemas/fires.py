"""
GEOWISE - Fire Data Schemas
app/schemas/fires.py

Pydantic schemas for NASA FIRMS fire detection data.

REQUEST SCHEMAS: Validate incoming API requests
RESPONSE SCHEMAS: Format outgoing API responses
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator

from app.schemas.common import (
    BoundingBox, DateRange, PaginationParams, PaginationMetadata,
    H3ResolutionEnum, GeoJSONFeatureCollection, ConfidenceLevel, SortOrder
)


# ============================================================================
# REQUEST SCHEMAS (Input Validation)
# ============================================================================

class FireQueryRequest(BaseModel):
    """
    Query fires by geographic area and time period.
    
    Used by: GET /api/v1/fires
    
    Example:
        {
            "bbox": {"lat_min": 23, "lon_min": 60, "lat_max": 37, "lon_max": 77.5},
            "start_date": "2025-01-01",
            "end_date": "2025-01-10",
            "min_frp": 10.0,
            "confidence": "h"
        }
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
    
    @validator('country_iso')
    def uppercase_country(cls, v):
        """Convert country code to uppercase"""
        return v.upper() if v else None
    
    @root_validator
    def validate_spatial_filter(cls, values):
        """Must provide either bbox OR country_iso"""
        bbox = values.get('bbox')
        country = values.get('country_iso')
        
        if not bbox and not country:
            raise ValueError('Must provide either bbox or country_iso')
        
        if bbox and country:
            raise ValueError('Provide only one: bbox or country_iso')
        
        return values
    
    @root_validator
    def validate_temporal_filter(cls, values):
        """
        Must provide either (start_date + end_date) OR days.
        
        NASA FIRMS only has last 10 days of data.
        """
        start = values.get('start_date')
        end = values.get('end_date')
        days = values.get('days')
        
        if days:
            # Using 'days' - ignore start/end dates
            if start or end:
                raise ValueError('When using "days", do not provide start_date or end_date')
        else:
            # Using date range - both required
            if not start or not end:
                raise ValueError('Must provide both start_date and end_date, or use "days"')
            
            if end < start:
                raise ValueError('end_date must be after start_date')
            
            # Check if date range exceeds 10 days
            days_diff = (end - start).days + 1
            if days_diff > 10:
                raise ValueError('NASA FIRMS data limited to 10 days. Use smaller date range.')
        
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "country_iso": "PAK",
                "days": 7,
                "min_frp": 10.0,
                "confidence": "h",
                "limit": 100
            }
        }


class FireAggregationRequest(BaseModel):
    """
    Request aggregated fire statistics at H3 resolution.
    
    Used by: GET /api/v1/fires/aggregated
    
    For map visualization - returns hexagons instead of individual fires.
    """
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
    
    @root_validator
    def validate_filters(cls, values):
        """Same validations as FireQueryRequest"""
        # Check spatial filter
        bbox = values.get('bbox')
        country = values.get('country_iso')
        if not bbox and not country:
            raise ValueError('Must provide either bbox or country_iso')
        if bbox and country:
            raise ValueError('Provide only one: bbox or country_iso')
        
        # Check temporal filter
        start = values.get('start_date')
        end = values.get('end_date')
        days = values.get('days')
        
        if not days and not (start and end):
            raise ValueError('Must provide date range or days')
        
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "country_iso": "PAK",
                "days": 7,
                "resolution": 9,
                "format": "geojson"
            }
        }


# ============================================================================
# RESPONSE SCHEMAS (Output Formatting)
# ============================================================================

class FireDetectionResponse(BaseModel):
    """
    Single fire detection record.
    
    Converted from SQLAlchemy FireDetection model for API response.
    """
    id: str = Field(..., description="Unique fire detection ID")
    
    # Location
    latitude: float = Field(..., description="Latitude in decimal degrees")
    longitude: float = Field(..., description="Longitude in decimal degrees")
    
    # H3 indexes (for different zoom levels)
    h3_index_9: str = Field(..., description="H3 index at resolution 9 (174m)")
    h3_index_5: Optional[str] = Field(None, description="H3 index at resolution 5 (20km)")
    
    # Fire characteristics
    brightness: float = Field(..., description="Brightness temperature (Kelvin)")
    bright_ti5: Optional[float] = Field(None, description="Brightness temperature I-5")
    frp: Optional[float] = Field(None, description="Fire Radiative Power (MW)")
    
    # Detection metadata
    confidence: str = Field(..., description="Confidence: 'l' (low), 'n' (nominal), 'h' (high)")
    satellite: str = Field(..., description="Satellite identifier")
    instrument: Optional[str] = Field(None, description="Instrument name")
    
    # Temporal
    acq_date: datetime = Field(..., description="Acquisition date/time (UTC)")
    acq_time: Optional[str] = Field(None, description="Acquisition time (HHMM)")
    daynight: Optional[str] = Field(None, description="'D' (day) or 'N' (night)")
    
    class Config:
        orm_mode = True  # Allow conversion from SQLAlchemy model
        schema_extra = {
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


class FireListResponse(BaseModel):
    """
    Paginated list of fire detections.
    
    Used by: GET /api/v1/fires
    """
    fires: List[FireDetectionResponse] = Field(..., description="List of fire detections")
    pagination: PaginationMetadata = Field(..., description="Pagination info")
    summary: Optional[Dict[str, Any]] = Field(None, description="Summary statistics")
    
    class Config:
        schema_extra = {
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


class FireAggregationCell(BaseModel):
    """
    Aggregated fire statistics for one H3 hexagon.
    """
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
    
    class Config:
        schema_extra = {
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


class FireAggregationResponse(BaseModel):
    """
    Aggregated fire data at H3 resolution.
    
    Can return as GeoJSON (for maps) or regular JSON (for charts).
    """
    cells: List[FireAggregationCell] = Field(..., description="Aggregated H3 cells")
    metadata: Dict[str, Any] = Field(..., description="Query metadata")
    summary: Dict[str, Any] = Field(..., description="Overall statistics")
    
    class Config:
        schema_extra = {
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


class FireStatisticsResponse(BaseModel):
    """
    Overall fire statistics for a region/time period.
    
    Used by: GET /api/v1/fires/statistics
    """
    total_fires: int = Field(..., description="Total fire count")
    date_range: Dict[str, str] = Field(..., description="Date range analyzed")
    region: str = Field(..., description="Region identifier")
    
    # Intensity statistics
    frp_statistics: Dict[str, float] = Field(..., description="FRP stats (min, max, avg, total)")
    brightness_statistics: Dict[str, float] = Field(..., description="Brightness stats")
    
    # Confidence distribution
    confidence_distribution: Dict[str, int] = Field(..., description="Count by confidence level")
    
    # Temporal distribution
    fires_by_date: List[Dict[str, Any]] = Field(..., description="Daily fire counts")
    
    # Spatial distribution
    fires_by_h3: List[Dict[str, Any]] = Field(..., description="Fire counts by H3 cell")
    
    class Config:
        schema_extra = {
            "example": {
                "total_fires": 3416,
                "date_range": {
                    "start": "2025-01-01",
                    "end": "2025-01-10"
                },
                "region": "PAK",
                "frp_statistics": {
                    "min": 2.1,
                    "max": 45.7,
                    "avg": 12.3,
                    "total": 42028.8
                },
                "confidence_distribution": {
                    "high": 2890,
                    "nominal": 450,
                    "low": 76
                }
            }
        }


# ============================================================================
# GEOJSON RESPONSE SCHEMAS
# ============================================================================

class FireGeoJSONResponse(GeoJSONFeatureCollection):
    """
    Fire data in GeoJSON format for mapping.
    
    Extends base GeoJSON schema with fire-specific metadata.
    """
    metadata: Dict[str, Any] = Field(default_factory=lambda: {
        "source": "NASA FIRMS",
        "dataset": "VIIRS_SNPP_NRT",
        "resolution": "375m"
    })


# Example usage
if __name__ == "__main__":
    """Test fire schemas"""
    
    # Test FireQueryRequest
    query = FireQueryRequest(
        country_iso="PAK",
        days=7,
        min_frp=10.0,
        confidence=ConfidenceLevel.HIGH,
        limit=100
    )
    print(f"✅ FireQueryRequest: {query.country_iso}, {query.days} days")
    
    # Test FireAggregationRequest
    agg_req = FireAggregationRequest(
        country_iso="PAK",
        days=7,
        resolution=H3ResolutionEnum.DISPLAY
    )
    print(f"✅ FireAggregationRequest: Resolution {agg_req.resolution}")
    
    print("\n✅ Fire schemas loaded successfully!")