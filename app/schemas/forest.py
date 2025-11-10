"""
GEOWISE - Forest Data Schemas
app/schemas/forest.py

Pydantic schemas for Global Forest Watch (GFW) forest data.

NOTE: Forest data comes from GFW API (not stored in database).
These schemas validate requests and format API responses.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator

from app.schemas.common import H3ResolutionEnum


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class ForestStatsRequest(BaseModel):
    """
    Request forest statistics for a country.
    
    Used by: GET /api/v1/forest/stats
    
    Example:
        GET /api/v1/forest/stats?country_iso=PAK&start_year=2001&end_year=2024
    """
    country_iso: str = Field(..., min_length=3, max_length=3, 
                            description="3-letter ISO country code")
    
    start_year: Optional[int] = Field(None, ge=2001, le=2024,
                                     description="Start year for analysis (GFW data from 2001)")
    end_year: Optional[int] = Field(None, ge=2001, le=2024,
                                   description="End year for analysis")
    
    @validator('country_iso')
    def uppercase_country(cls, v):
        """Convert to uppercase"""
        return v.upper()
    
    @validator('end_year')
    def end_after_start(cls, v, values):
        """Ensure end_year >= start_year"""
        start = values.get('start_year')
        if start and v and v < start:
            raise ValueError('end_year must be >= start_year')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "country_iso": "PAK",
                "start_year": 2001,
                "end_year": 2024
            }
        }


class ForestTrendRequest(BaseModel):
    """
    Request deforestation trend analysis.
    
    Used by: GET /api/v1/forest/trend
    """
    country_iso: str = Field(..., min_length=3, max_length=3)
    
    comparison_period_years: int = Field(
        default=5, ge=1, le=10,
        description="Years to compare (e.g., 5 = compare first 5 vs last 5 years)"
    )
    
    @validator('country_iso')
    def uppercase_country(cls, v):
        return v.upper()
    
    class Config:
        schema_extra = {
            "example": {
                "country_iso": "PAK",
                "comparison_period_years": 5
            }
        }


class ForestTileRequest(BaseModel):
    """
    Request forest tile configuration for map visualization.
    
    Used by: GET /api/v1/forest/tiles
    
    Returns tile URLs for frontend to directly request from GFW servers.
    """
    layers: Optional[List[str]] = Field(
        default=["tree_cover_loss", "tree_cover_density"],
        description="Tile layers to include"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "layers": ["tree_cover_loss", "tree_cover_density", "tree_cover_gain"]
            }
        }


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class YearlyForestLoss(BaseModel):
    """
    Forest loss for a single year.
    """
    year: int = Field(..., description="Year")
    loss_hectares: float = Field(..., description="Forest loss in hectares")
    loss_km2: Optional[float] = Field(None, description="Forest loss in square kilometers")
    
    @validator('loss_km2', always=True)
    def calculate_km2(cls, v, values):
        """Auto-calculate km² from hectares if not provided"""
        if v is None and 'loss_hectares' in values:
            return values['loss_hectares'] / 100  # 1 km² = 100 hectares
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "year": 2024,
                "loss_hectares": 3456.0,
                "loss_km2": 34.56
            }
        }


class ForestStatsResponse(BaseModel):
    """
    Comprehensive forest statistics for a country.
    
    Response from: GET /api/v1/forest/stats
    """
    country_iso: str = Field(..., description="Country ISO code")
    country_name: str = Field(..., description="Country name")
    geostore_id: str = Field(..., description="GFW geostore identifier")
    
    # Overall statistics
    total_loss_hectares: float = Field(..., description="Total forest loss (all years)")
    total_loss_km2: float = Field(..., description="Total forest loss in km²")
    
    # Time period
    data_range: str = Field(..., description="Years covered (e.g., '2001-2024')")
    years_available: int = Field(..., description="Number of years with data")
    
    # Recent data
    most_recent_year: int = Field(..., description="Most recent year available")
    recent_loss_hectares: float = Field(..., description="Loss in most recent year")
    
    # Yearly breakdown
    yearly_data: List[YearlyForestLoss] = Field(..., description="Year-by-year forest loss")
    
    # Metadata
    last_updated: datetime = Field(..., description="When data was last fetched")
    source: str = Field(default="Global Forest Watch", description="Data source")
    
    class Config:
        schema_extra = {
            "example": {
                "country_iso": "PAK",
                "country_name": "Pakistan",
                "geostore_id": "abc123xyz",
                "total_loss_hectares": 79188.0,
                "total_loss_km2": 791.88,
                "data_range": "2001-2024",
                "years_available": 24,
                "most_recent_year": 2024,
                "recent_loss_hectares": 3456.0,
                "yearly_data": [],
                "last_updated": "2025-01-15T10:30:00Z",
                "source": "Global Forest Watch"
            }
        }


class DeforestationTrend(str):
    """Deforestation trend classification"""
    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    STABLE = "STABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class TrendSeverity(str):
    """Severity of deforestation trend"""
    HIGH = "HIGH"          # Change > 50%
    MODERATE = "MODERATE"  # Change 10-50%
    NEUTRAL = "NEUTRAL"    # Change < 10%
    POSITIVE = "POSITIVE"  # Decreasing deforestation


class ForestTrendResponse(BaseModel):
    """
    Deforestation trend analysis results.
    
    Response from: GET /api/v1/forest/trend
    
    Compares early period vs recent period to identify trends.
    """
    country_iso: str = Field(..., description="Country ISO code")
    country_name: str = Field(..., description="Country name")
    
    # Trend classification
    trend: str = Field(..., description="INCREASING, DECREASING, or STABLE")
    severity: str = Field(..., description="HIGH, MODERATE, NEUTRAL, or POSITIVE")
    
    # Change metrics
    change_percent: float = Field(..., description="Percentage change (positive = worsening)")
    
    # Period comparison
    analysis_period: str = Field(..., description="Years analyzed (e.g., '2001-2024')")
    early_period_avg_loss_ha: float = Field(..., description="Average loss in early years")
    recent_period_avg_loss_ha: float = Field(..., description="Average loss in recent years")
    
    # Overall statistics
    total_loss_hectares: float = Field(..., description="Total loss across all years")
    
    # Interpretation
    interpretation: str = Field(..., description="Human-readable trend interpretation")
    
    class Config:
        schema_extra = {
            "example": {
                "country_iso": "PAK",
                "country_name": "Pakistan",
                "trend": "INCREASING",
                "severity": "MODERATE",
                "change_percent": 23.5,
                "analysis_period": "2001-2024",
                "early_period_avg_loss_ha": 2890.0,
                "recent_period_avg_loss_ha": 3568.0,
                "total_loss_hectares": 79188.0,
                "interpretation": "Deforestation is INCREASING at a MODERATE rate. Recent years show 23.5% more forest loss compared to early period."
            }
        }


class TileLayerConfig(BaseModel):
    """
    Configuration for a single tile layer.
    """
    layer_id: str = Field(..., description="Layer identifier")
    tile_url: str = Field(..., description="Tile URL template with {z}/{x}/{y}")
    description: str = Field(..., description="Layer description")
    min_zoom: int = Field(..., description="Minimum zoom level")
    max_zoom: int = Field(..., description="Maximum zoom level")
    attribution: Optional[str] = Field(None, description="Attribution text")
    
    class Config:
        schema_extra = {
            "example": {
                "layer_id": "tree_cover_loss",
                "tile_url": "https://tiles.globalforestwatch.org/umd_tree_cover_loss/v1.9/tcd_30/{z}/{x}/{y}.png",
                "description": "Annual tree cover loss (2001-2024)",
                "min_zoom": 3,
                "max_zoom": 12,
                "attribution": "Data: Global Forest Watch"
            }
        }


class ForestTileResponse(BaseModel):
    """
    Tile layer configuration for map visualization.
    
    Response from: GET /api/v1/forest/tiles
    
    Frontend uses these URLs to directly request tiles from GFW servers.
    """
    tile_layers: Dict[str, TileLayerConfig] = Field(..., description="Available tile layers")
    usage_instructions: str = Field(
        default="Use tile URLs in Mapbox/Leaflet as raster sources",
        description="How to use these tiles"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "tile_layers": {
                    "tree_cover_loss": {
                        "layer_id": "tree_cover_loss",
                        "tile_url": "https://tiles.globalforestwatch.org/.../tcd_30/{z}/{x}/{y}.png",
                        "description": "Annual tree cover loss (2001-2024)",
                        "min_zoom": 3,
                        "max_zoom": 12
                    }
                },
                "usage_instructions": "Use tile URLs in Mapbox/Leaflet as raster sources"
            }
        }


class ForestHealthCheckResponse(BaseModel):
    """
    GFW API health check response.
    
    Response from: GET /api/v1/forest/health
    """
    status: str = Field(..., description="'healthy' or 'unhealthy'")
    api_accessible: bool = Field(..., description="Whether GFW API is accessible")
    status_code: Optional[int] = Field(None, description="HTTP status code from GFW")
    base_url: str = Field(..., description="GFW API base URL")
    timestamp: datetime = Field(..., description="Health check timestamp")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "api_accessible": True,
                "status_code": 200,
                "base_url": "https://data-api.globalforestwatch.org",
                "timestamp": "2025-01-15T10:30:00Z"
            }
        }


class AvailableCountriesResponse(BaseModel):
    """
    List of countries with available forest data.
    
    Response from: GET /api/v1/forest/countries
    """
    countries: List[Dict[str, str]] = Field(..., description="List of countries with ISO codes")
    total: int = Field(..., description="Total number of countries")
    note: str = Field(
        default="GFW supports all countries. This is a commonly requested subset.",
        description="Usage note"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "countries": [
                    {"iso": "PAK", "name": "Pakistan"},
                    {"iso": "IND", "name": "India"},
                    {"iso": "BRA", "name": "Brazil"}
                ],
                "total": 3,
                "note": "GFW supports all countries. This is a commonly requested subset."
            }
        }


# Example usage
if __name__ == "__main__":
    """Test forest schemas"""
    
    # Test ForestStatsRequest
    stats_req = ForestStatsRequest(
        country_iso="PAK",
        start_year=2001,
        end_year=2024
    )
    print(f"✅ ForestStatsRequest: {stats_req.country_iso} ({stats_req.start_year}-{stats_req.end_year})")
    
    # Test YearlyForestLoss auto-calculation
    yearly = YearlyForestLoss(year=2024, loss_hectares=3456.0)
    print(f"✅ YearlyForestLoss: {yearly.loss_hectares} ha = {yearly.loss_km2} km²")
    
    print("\n✅ Forest schemas loaded successfully!")