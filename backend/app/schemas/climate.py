"""
GEOWISE - Climate Data Schemas
app/schemas/climate.py

Pydantic schemas for Open-Meteo climate data (ERA5 reanalysis).
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.schemas.common import Point, DateRange


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class ClimateQueryRequest(BaseModel):
    """Request historical climate data for a location."""
    # Location
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    
    # Time period
    start_date: date = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: date = Field(..., description="End date (YYYY-MM-DD)")
    
    # Optional parameters
    include_soil_moisture: bool = Field(
        default=False,
        description="Include soil moisture data"
    )
    
    @field_validator('end_date')
    @classmethod
    def end_after_start(cls, v, info):
        """Ensure end_date >= start_date"""
        start = info.data.get('start_date')
        if start and v < start:
            raise ValueError('end_date must be on or after start_date')
        return v
    
    @field_validator('end_date')
    @classmethod
    def not_future(cls, v):
        """Prevent querying future dates"""
        if v > date.today():
            raise ValueError('end_date cannot be in the future')
        return v
    
    def days_count(self) -> int:
        """Calculate number of days in query"""
        return (self.end_date - self.start_date).days + 1
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "latitude": 30.3753,
                "longitude": 69.3451,
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "include_soil_moisture": False
            }
        }
    )


class ClimateCountrySummaryRequest(BaseModel):
    """Request climate summary for a country."""
    country_iso: str = Field(..., min_length=3, max_length=3, 
                            description="3-letter ISO country code")
    
    start_date: date = Field(..., description="Start date")
    end_date: date = Field(..., description="End date")
    
    sample_points: Optional[List[Point]] = Field(
        None,
        description="Custom sample points"
    )
    
    include_soil_moisture: bool = Field(default=False)
    
    @field_validator('country_iso')
    @classmethod
    def uppercase_country(cls, v):
        return v.upper()
    
    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        start = info.data.get('start_date')
        if start and v < start:
            raise ValueError('end_date must be >= start_date')
        if v > date.today():
            raise ValueError('end_date cannot be in the future')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "country_iso": "PAK",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "sample_points": None,
                "include_soil_moisture": False
            }
        }
    )


class FireRiskAssessmentRequest(BaseModel):
    """Request fire risk assessment based on climate conditions."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    
    start_date: date = Field(...)
    end_date: date = Field(...)
    
    # Risk thresholds
    high_temp_threshold: float = Field(default=30.0, description="°C above which fire risk increases")
    low_precip_threshold: float = Field(default=1.0, description="mm/day below which fire risk increases")
    high_wind_threshold: float = Field(default=20.0, description="km/h above which fire risk increases")
    low_soil_moisture_threshold: float = Field(default=0.2, description="m³/m³ below which fire risk increases")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "latitude": 30.5,
                "longitude": 70.5,
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "high_temp_threshold": 30.0,
                "low_precip_threshold": 1.0
            }
        }
    )


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class DailyClimateData(BaseModel):
    """Climate data for a single day."""
    date: date = Field(..., description="Date (YYYY-MM-DD)")
    
    # Temperature (°C)
    temperature_max: Optional[float] = Field(None, description="Maximum temperature (°C)")
    temperature_min: Optional[float] = Field(None, description="Minimum temperature (°C)")
    temperature_mean: Optional[float] = Field(None, description="Mean temperature (°C)")
    
    # Precipitation (mm)
    precipitation_sum: Optional[float] = Field(None, description="Total precipitation (mm)")
    
    # Wind (km/h)
    windspeed_max: Optional[float] = Field(None, description="Maximum wind speed (km/h)")
    
    # Humidity (%)
    relative_humidity_mean: Optional[float] = Field(None, description="Mean relative humidity (%)")
    
    # Soil moisture (m³/m³)
    soil_moisture_0_7cm: Optional[float] = Field(None, description="Surface soil moisture (m³/m³)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2025-01-15",
                "temperature_max": 28.5,
                "temperature_min": 15.2,
                "precipitation_sum": 0.0,
                "windspeed_max": 12.3,
                "relative_humidity_mean": 45.6
            }
        }
    )


class ClimateTimeSeriesResponse(BaseModel):
    """Historical climate data as time series."""
    location: Point = Field(..., description="Query location")
    date_range: Dict[str, str] = Field(..., description="Date range queried")
    
    # Time series data
    daily_data: List[DailyClimateData] = Field(..., description="Daily climate measurements")
    
    # Summary statistics
    summary: Dict[str, Any] = Field(..., description="Statistical summary")
    
    # Metadata
    source: str = Field(default="Open-Meteo ERA5", description="Data source")
    resolution: str = Field(default="~25km", description="Native grid resolution")
    last_updated: datetime = Field(..., description="When data was fetched")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location": {"latitude": 30.3753, "longitude": 69.3451},
                "date_range": {"start": "2025-01-01", "end": "2025-01-31"},
                "daily_data": [],
                "summary": {"days": 31, "avg_temperature": 20.5},
                "source": "Open-Meteo ERA5",
                "resolution": "~25km",
                "last_updated": "2025-01-15T10:30:00Z"
            }
        }
    )


class ClimateStatistics(BaseModel):
    """Statistical summary of climate variables."""
    variable_name: str = Field(..., description="Climate variable name")
    unit: str = Field(..., description="Unit of measurement")
    
    count: int = Field(..., description="Number of valid measurements")
    min: Optional[float] = Field(None, description="Minimum value")
    max: Optional[float] = Field(None, description="Maximum value")
    mean: Optional[float] = Field(None, description="Mean value")
    total: Optional[float] = Field(None, description="Total (for precipitation)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "variable_name": "temperature_max",
                "unit": "°C",
                "count": 31,
                "min": 18.5,
                "max": 32.1,
                "mean": 26.3,
                "total": None
            }
        }
    )


class ClimateCountrySummaryResponse(BaseModel):
    """Climate summary for a country."""
    country_iso: str = Field(..., description="Country ISO code")
    date_range: Dict[str, str] = Field(..., description="Date range")
    
    sample_points_count: int = Field(..., description="Number of sample points used")
    sample_locations: List[Point] = Field(..., description="Locations sampled")
    
    climate_data: Dict[str, Any] = Field(..., description="Aggregated daily data")
    statistics: List[ClimateStatistics] = Field(..., description="Variable statistics")
    
    last_updated: datetime = Field(...)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "country_iso": "PAK",
                "date_range": {"start": "2025-01-01", "end": "2025-01-31"},
                "sample_points_count": 1,
                "sample_locations": [{"latitude": 30.3753, "longitude": 69.3451}],
                "climate_data": {},
                "statistics": [],
                "last_updated": "2025-01-15T10:30:00Z"
            }
        }
    )


class FireRiskLevel(str):
    """Fire risk classification"""
    EXTREME = "EXTREME"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


class FireRiskAssessmentResponse(BaseModel):
    """Fire risk assessment based on climate conditions."""
    location: Point = Field(..., description="Assessment location")
    date_range: Dict[str, str] = Field(..., description="Period analyzed")
    
    # Risk classification
    risk_level: str = Field(..., description="EXTREME, HIGH, MODERATE, or LOW")
    risk_score: float = Field(..., ge=0, le=100, description="Risk score (0-100)")
    
    # Contributing factors
    total_days: int = Field(..., description="Days analyzed")
    high_temp_days: int = Field(..., description="Days with high temperature")
    dry_days: int = Field(..., description="Days with low precipitation")
    windy_days: int = Field(..., description="Days with high wind")
    low_soil_moisture_days: int = Field(..., description="Days with low soil moisture")
    
    # Assessment details
    assessment: str = Field(..., description="Human-readable assessment")
    recommendations: Optional[List[str]] = Field(None, description="Risk mitigation recommendations")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location": {"latitude": 30.5, "longitude": 70.5},
                "date_range": {"start": "2025-01-01", "end": "2025-01-31"},
                "risk_level": "HIGH",
                "risk_score": 67.5,
                "total_days": 31,
                "high_temp_days": 25,
                "dry_days": 28,
                "windy_days": 15,
                "low_soil_moisture_days": 20,
                "assessment": "HIGH fire risk conditions detected",
                "recommendations": ["Monitor fire activity closely"]
            }
        }
    )


class ClimateHealthCheckResponse(BaseModel):
    """Open-Meteo API health check response."""
    status: str = Field(..., description="'healthy' or 'unhealthy'")
    api_accessible: bool = Field(..., description="Whether Open-Meteo API is accessible")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    base_url: str = Field(..., description="Open-Meteo API base URL")
    timestamp: datetime = Field(..., description="Health check timestamp")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "api_accessible": True,
                "status_code": 200,
                "base_url": "https://archive-api.open-meteo.com/v1/archive",
                "timestamp": "2025-01-15T10:30:00Z"
            }
        }
    )