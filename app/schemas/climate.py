"""
GEOWISE - Climate Data Schemas
app/schemas/climate.py

Pydantic schemas for Open-Meteo climate data (ERA5 reanalysis).

NOTE: Climate data is fetched from Open-Meteo API, not stored in database.
Native resolution: ~25km grid (coarsest dataset - determines analysis resolution).
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator

from app.schemas.common import Point, DateRange


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class ClimateQueryRequest(BaseModel):
    """
    Request historical climate data for a location.
    
    Used by: GET /api/v1/climate/historical
    
    Example:
        {
            "latitude": 30.3753,
            "longitude": 69.3451,
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "include_soil_moisture": false
        }
    """
    # Location
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    
    # Time period
    start_date: date = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: date = Field(..., description="End date (YYYY-MM-DD)")
    
    # Optional parameters
    include_soil_moisture: bool = Field(
        default=False,
        description="Include soil moisture data (may not be available for all regions/dates)"
    )
    
    @validator('end_date')
    def end_after_start(cls, v, values):
        """Ensure end_date >= start_date"""
        start = values.get('start_date')
        if start and v < start:
            raise ValueError('end_date must be on or after start_date')
        return v
    
    @validator('end_date')
    def not_future(cls, v):
        """Prevent querying future dates"""
        if v > date.today():
            raise ValueError('end_date cannot be in the future')
        return v
    
    def days_count(self) -> int:
        """Calculate number of days in query"""
        return (self.end_date - self.start_date).days + 1
    
    class Config:
        schema_extra = {
            "example": {
                "latitude": 30.3753,
                "longitude": 69.3451,
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "include_soil_moisture": False
            }
        }


class ClimateCountrySummaryRequest(BaseModel):
    """
    Request climate summary for a country.
    
    Used by: GET /api/v1/climate/country-summary
    
    Uses default country center point or multiple sample points for better coverage.
    """
    country_iso: str = Field(..., min_length=3, max_length=3, 
                            description="3-letter ISO country code")
    
    start_date: date = Field(..., description="Start date")
    end_date: date = Field(..., description="End date")
    
    # Optional: provide specific sample points instead of using country center
    sample_points: Optional[List[Point]] = Field(
        None,
        description="Custom sample points (if not provided, uses country center)"
    )
    
    include_soil_moisture: bool = Field(default=False)
    
    @validator('country_iso')
    def uppercase_country(cls, v):
        return v.upper()
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        start = values.get('start_date')
        if start and v < start:
            raise ValueError('end_date must be >= start_date')
        if v > date.today():
            raise ValueError('end_date cannot be in the future')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "country_iso": "PAK",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "sample_points": None,
                "include_soil_moisture": False
            }
        }


class FireRiskAssessmentRequest(BaseModel):
    """
    Request fire risk assessment based on climate conditions.
    
    Used by: POST /api/v1/climate/fire-risk
    
    Analyzes temperature, precipitation, wind, and soil moisture.
    """
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    
    start_date: date = Field(...)
    end_date: date = Field(...)
    
    # Risk thresholds (optional - uses defaults if not provided)
    high_temp_threshold: float = Field(default=30.0, description="°C above which fire risk increases")
    low_precip_threshold: float = Field(default=1.0, description="mm/day below which fire risk increases")
    high_wind_threshold: float = Field(default=20.0, description="km/h above which fire risk increases")
    low_soil_moisture_threshold: float = Field(default=0.2, description="m³/m³ below which fire risk increases")
    
    class Config:
        schema_extra = {
            "example": {
                "latitude": 30.5,
                "longitude": 70.5,
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "high_temp_threshold": 30.0,
                "low_precip_threshold": 1.0
            }
        }


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class DailyClimateData(BaseModel):
    """
    Climate data for a single day.
    """
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
    
    # Soil moisture (m³/m³) - optional
    soil_moisture_0_7cm: Optional[float] = Field(None, description="Surface soil moisture (m³/m³)")
    
    class Config:
        schema_extra = {
            "example": {
                "date": "2025-01-15",
                "temperature_max": 28.5,
                "temperature_min": 15.2,
                "precipitation_sum": 0.0,
                "windspeed_max": 12.3,
                "relative_humidity_mean": 45.6
            }
        }


class ClimateTimeSeriesResponse(BaseModel):
    """
    Historical climate data as time series.
    
    Response from: GET /api/v1/climate/historical
    """
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
    
    class Config:
        schema_extra = {
            "example": {
                "location": {"latitude": 30.3753, "longitude": 69.3451},
                "date_range": {"start": "2025-01-01", "end": "2025-01-31"},
                "daily_data": [],
                "summary": {
                    "days": 31,
                    "avg_temperature": 20.5,
                    "total_precipitation": 15.3
                },
                "source": "Open-Meteo ERA5",
                "resolution": "~25km",
                "last_updated": "2025-01-15T10:30:00Z"
            }
        }


class ClimateStatistics(BaseModel):
    """
    Statistical summary of climate variables.
    """
    variable_name: str = Field(..., description="Climate variable name")
    unit: str = Field(..., description="Unit of measurement")
    
    count: int = Field(..., description="Number of valid measurements")
    min: Optional[float] = Field(None, description="Minimum value")
    max: Optional[float] = Field(None, description="Maximum value")
    mean: Optional[float] = Field(None, description="Mean value")
    total: Optional[float] = Field(None, description="Total (for precipitation)")
    
    class Config:
        schema_extra = {
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


class ClimateCountrySummaryResponse(BaseModel):
    """
    Climate summary for a country (aggregated from sample points).
    
    Response from: GET /api/v1/climate/country-summary
    """
    country_iso: str = Field(..., description="Country ISO code")
    date_range: Dict[str, str] = Field(..., description="Date range")
    
    sample_points_count: int = Field(..., description="Number of sample points used")
    sample_locations: List[Point] = Field(..., description="Locations sampled")
    
    # Aggregated climate data (averaged across sample points)
    climate_data: Dict[str, Any] = Field(..., description="Aggregated daily data")
    
    # Statistics
    statistics: List[ClimateStatistics] = Field(..., description="Variable statistics")
    
    last_updated: datetime = Field(...)
    
    class Config:
        schema_extra = {
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


class FireRiskLevel(str):
    """Fire risk classification"""
    EXTREME = "EXTREME"  # Risk score > 70
    HIGH = "HIGH"        # Risk score 50-70
    MODERATE = "MODERATE"  # Risk score 30-50
    LOW = "LOW"          # Risk score < 30


class FireRiskAssessmentResponse(BaseModel):
    """
    Fire risk assessment based on climate conditions.
    
    Response from: POST /api/v1/climate/fire-risk
    
    Analyzes multiple fire risk factors to produce overall risk score.
    """
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
    
    class Config:
        schema_extra = {
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
                "recommendations": [
                    "Monitor fire activity closely",
                    "Restrict outdoor burning"
                ]
            }
        }


class ClimateHealthCheckResponse(BaseModel):
    """
    Open-Meteo API health check response.
    
    Response from: GET /api/v1/climate/health
    """
    status: str = Field(..., description="'healthy' or 'unhealthy'")
    api_accessible: bool = Field(..., description="Whether Open-Meteo API is accessible")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    base_url: str = Field(..., description="Open-Meteo API base URL")
    timestamp: datetime = Field(..., description="Health check timestamp")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "api_accessible": True,
                "status_code": 200,
                "base_url": "https://archive-api.open-meteo.com/v1/archive",
                "timestamp": "2025-01-15T10:30:00Z"
            }
        }


# Example usage
if __name__ == "__main__":
    """Test climate schemas"""
    
    # Test ClimateQueryRequest
    query = ClimateQueryRequest(
        latitude=30.3753,
        longitude=69.3451,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31)
    )
    print(f"✅ ClimateQueryRequest: ({query.latitude}, {query.longitude}), {query.days_count()} days")
    
    # Test DailyClimateData
    daily = DailyClimateData(
        date=date(2025, 1, 15),
        temperature_max=28.5,
        temperature_min=15.2,
        precipitation_sum=0.0
    )
    print(f"✅ DailyClimateData: {daily.date}, temp: {daily.temperature_min}°C - {daily.temperature_max}°C")
    
    print("\n✅ Climate schemas loaded successfully!")