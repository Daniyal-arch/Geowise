"""
GEOWISE Configuration Settings
Centralized settings management using Pydantic with environment variable support.
"""
from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from pathlib import Path
from dotenv import load_dotenv

# Force load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Settings(BaseSettings):
    """GEOWISE Application Settings"""
    
    # Application
    APP_NAME: str = "GEOWISE API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    
    # API
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000","http://localhost:8080"],
        description="Allowed CORS origins"
    )
    
    # Database (SQLite for development)
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./geowise.db",
        description="SQLAlchemy database connection string"
    )
    
    # Redis (for caching and Celery)
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # External APIs
    NASA_FIRMS_API_KEY: Optional[str] = Field(
        default=None,
        description="NASA FIRMS API key for fire data"
    )
    NASA_FIRMS_BASE_URL: str = Field(
        default="https://firms.modaps.eosdis.nasa.gov/api/area/csv",
        description="NASA FIRMS API base URL"
    )
    
    GFW_API_KEY: Optional[str] = Field(
        default="8e5b3b69-fa31-4eef-af79-eec9674c7014",
        description="Global Forest Watch API key"
    )
    GFW_TILES_BASE_URL: str = Field(
        default="https://tiles.globalforestwatch.org",
        description="Global Forest Watch tiles base URL"
    )
    
    OPEN_METEO_BASE_URL: str = Field(
        default="https://archive-api.open-meteo.com/v1/archive",
        description="Open-Meteo climate data API"
    )
    
    WORLD_BANK_BASE_URL: str = Field(
        default="https://api.worldbank.org/v2",
        description="World Bank API base URL"
    )
    
    # LLM Services
    GROQ_API_KEY: Optional[str] = Field(
        default=None,
        description="Groq API key for LLM inference"
    )
    GROQ_MODEL: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model to use for inference"
    )
    
    # H3 Spatial Configuration
    H3_DISPLAY_RESOLUTION: int = Field(
        default=9,
        description="H3 resolution for display tiles (1km grid)"
    )
    H3_ANALYSIS_RESOLUTION: int = Field(
        default=5,
        description="H3 resolution for statistical analysis (25km grid)"
    )
    
    # Cache Settings
    CACHE_TTL: int = Field(
        default=3600,
        description="Default cache TTL in seconds"
    )
    
    # Celery Background Tasks
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            if v.startswith('['):
                import json
                return json.loads(v)
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        """Ensure database URL is valid."""
        if not v:
            raise ValueError("DATABASE_URL must be set")
        return v
    
    @validator("H3_DISPLAY_RESOLUTION", "H3_ANALYSIS_RESOLUTION")
    def validate_h3_resolution(cls, v):
        """Ensure H3 resolution is valid (0-15)."""
        if not 0 <= v <= 15:
            raise ValueError("H3 resolution must be between 0 and 15")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()