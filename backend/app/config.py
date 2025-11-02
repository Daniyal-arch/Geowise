# backend/app/config.py
"""
Application configuration using Pydantic Settings.

WHY PYDANTIC SETTINGS?
-----------------------
1. Type validation (catches wrong types at startup, not runtime)
2. Environment variable loading (.env file)
3. Default values with validation
4. Documentation (Field descriptions become OpenAPI docs)
5. IDE autocomplete (typed settings object)

DESIGN PATTERN: Single Source of Truth
---------------------------------------
- All configuration in one place
- No scattered config values
- Easy to see what's configurable
- Type-safe access: settings.DATABASE_URL (not os.getenv(...))

ENVIRONMENT VARIABLES:
----------------------
Load from:  1. Environment variables (highest priority)
            2. .env file (development)
            3. Defaults (fallback)

Example .env file:
    ENVIRONMENT=development
    DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/geowise
    REDIS_URL=redis://localhost:6379/0
    NASA_FIRMS_API_KEY=your_key_here
"""

from typing import Optional, List
from pydantic import Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import secrets


# ============================================================================
# SETTINGS CLASS
# ============================================================================
class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    HOW TO USE:
    -----------
    ```python
    from app.config import settings
    
    print(settings.DATABASE_URL)  # Type-safe access
    if settings.is_development:   # Computed property
        print("Running in dev mode")
    ```
    
    WHY CAPITAL LETTERS?
    - Convention for constants/config
    - Easy to distinguish from regular variables
    - Matches environment variable names
    """
    
    # ========================================================================
    # GENERAL SETTINGS
    # ========================================================================
    PROJECT_NAME: str = Field(
        default="GEOWISE",
        description="Project name used in API docs"
    )
    
    VERSION: str = Field(
        default="1.0.0",
        description="API version"
    )
    
    API_V1_PREFIX: str = Field(
        default="/api/v1",
        description="API route prefix"
    )
    
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )
    
    DEBUG: bool = Field(
        default=True,
        description="Enable debug mode (detailed errors, auto-reload)"
    )
    
    # ========================================================================
    # DATABASE SETTINGS
    # ========================================================================
    # WHY ASYNC DATABASE?
    # - FastAPI is async by default
    # - Sync DB would block event loop (slow!)
    # - Use asyncpg driver (fastest PostgreSQL driver)
    
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://geowise:geowise123@localhost:5432/geowise",
        description="Async PostgreSQL connection string"
    )
    
    # Connection pool settings
    # WHY POOL?
    # - Creating DB connections is slow (~50ms)
    # - Reusing connections is fast (~1ms)
    # - Pool size = max concurrent DB operations
    DB_POOL_SIZE: int = Field(
        default=10,
        description="Number of connections to keep in pool"
    )
    
    DB_MAX_OVERFLOW: int = Field(
        default=20,
        description="Max connections beyond pool_size (temporary)"
    )
    
    # WHY ECHO_SQL?
    # - Development: See all SQL queries (debugging)
    # - Production: Disable (too verbose, performance hit)
    DB_ECHO_SQL: bool = Field(
        default=False,
        description="Log all SQL queries"
    )
    
    # ========================================================================
    # REDIS SETTINGS (Cache & Celery)
    # ========================================================================
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    
    # Cache TTLs (Time To Live)
    # WHY DIFFERENT TTLs?
    # - Tiles change rarely → cache long (1 week)
    # - Fire data changes hourly → cache short (1 hour)
    # - Statistics change daily → cache medium (1 day)
    CACHE_TTL_TILES: int = Field(
        default=604800,  # 7 days
        description="Tile cache duration (seconds)"
    )
    
    CACHE_TTL_FIRES: int = Field(
        default=3600,  # 1 hour
        description="Fire data cache duration"
    )
    
    CACHE_TTL_ANALYSIS: int = Field(
        default=86400,  # 1 day
        description="Analysis results cache duration"
    )
    
    # ========================================================================
    # EXTERNAL API KEYS
    # ========================================================================
    NASA_FIRMS_API_KEY: Optional[str] = Field(
        default=None,
        description="NASA FIRMS MAP KEY (required for fire data)"
    )
    
    # GFW uses tile servers (no key needed)
    # Open-Meteo is free (no key needed)
    # World Bank is free (no key needed)
    
    # ========================================================================
    # LLM SETTINGS (Groq API)
    # ========================================================================
    GROQ_API_KEY: Optional[str] = Field(
        default=None,
        description="Groq API key for LLM queries"
    )
    
    GROQ_MODEL: str = Field(
        default="llama-3.1-70b-versatile",
        description="Groq model to use"
    )
    
    GROQ_MAX_TOKENS: int = Field(
        default=2048,
        description="Max tokens for LLM responses"
    )
    
    GROQ_TEMPERATURE: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="LLM temperature (0=deterministic, 2=creative)"
    )
    
    # ========================================================================
    # SPATIAL ANALYSIS SETTINGS
    # ========================================================================
    # H3 resolutions for different use cases
    # WHY MULTIPLE RESOLUTIONS?
    # - Resolution 9 (~174m): Visualization (map display)
    # - Resolution 6 (~20km): Analysis (statistics)
    # - Resolution 5 (~25km): Climate data aggregation
    H3_RESOLUTION_DISPLAY: int = Field(
        default=9,
        ge=0,
        le=15,
        description="H3 resolution for map visualization"
    )
    
    H3_RESOLUTION_ANALYSIS: int = Field(
        default=5,
        ge=0,
        le=15,
        description="H3 resolution for statistical analysis"
    )
    
    # Minimum data points for correlations
    # WHY 30?
    # - Central Limit Theorem applies at n≥30
    # - Below that, p-values unreliable
    MIN_CORRELATION_POINTS: int = Field(
        default=30,
        description="Minimum data points for correlation analysis"
    )
    
    # ========================================================================
    # HTTP CLIENT SETTINGS
    # ========================================================================
    # Timeouts for external APIs
    # WHY DIFFERENT TIMEOUTS?
    # - NASA FIRMS: Large datasets (30s)
    # - GFW tiles: Small images (10s)
    # - Open-Meteo: JSON responses (15s)
    REQUEST_TIMEOUT_GENERAL: int = Field(
        default=30,
        description="Default HTTP request timeout (seconds)"
    )
    
    REQUEST_TIMEOUT_TILES: int = Field(
        default=10,
        description="Tile request timeout (seconds)"
    )
    
    # Retry configuration
    # WHY RETRY?
    # - Networks are unreliable
    # - Transient errors common (503, timeouts)
    # - Exponential backoff prevents hammering
    REQUEST_MAX_RETRIES: int = Field(
        default=3,
        description="Max retry attempts for failed requests"
    )
    
    REQUEST_RETRY_BACKOFF: float = Field(
        default=2.0,
        description="Exponential backoff factor"
    )
    
    # ========================================================================
    # CORS SETTINGS (Frontend access)
    # ========================================================================
    # WHY CORS?
    # - Browser security: frontend (localhost:3000) calling backend (localhost:8000)
    # - Must explicitly allow origins
    # - Production: Only allow specific domains
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",  # React dev server
            "http://localhost:3001",  # Alternative port
        ],
        description="Allowed CORS origins"
    )
    
    CORS_ALLOW_CREDENTIALS: bool = Field(
        default=True,
        description="Allow cookies in CORS requests"
    )
    
    # ========================================================================
    # FILE STORAGE
    # ========================================================================
    DATA_DIR: Path = Field(
        default=Path("data"),
        description="Base directory for data storage"
    )
    
    TILES_DIR: Path = Field(
        default=Path("data/tiles"),
        description="Cache directory for map tiles"
    )
    
    CHROMA_DIR: Path = Field(
        default=Path("data/chroma"),
        description="Chroma vector database directory"
    )
    
    # ========================================================================
    # SECURITY (Future: Authentication)
    # ========================================================================
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT/sessions"
    )
    
    # WHY GENERATE SECRET_KEY?
    # - If not provided, create random one
    # - Different each run (sessions don't persist)
    # - Production: MUST set via environment variable
    
    # ========================================================================
    # PYDANTIC CONFIGURATION
    # ========================================================================
    model_config = SettingsConfigDict(
        # Where to load .env file from
        env_file=".env",
        env_file_encoding="utf-8",
        
        # Ignore extra fields in .env (forward compatibility)
        extra="ignore",
        
        # Case-insensitive environment variables
        case_sensitive=False,
    )
    
    # ========================================================================
    # VALIDATORS (Data validation on load)
    # ========================================================================
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """
        Ensure environment is valid.
        
        WHY VALIDATE?
        - Catch typos at startup (not at runtime)
        - Example: ENVIRONMENT=developmen (missing 't')
        """
        allowed = {"development", "staging", "production"}
        if v.lower() not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of: {allowed}")
        return v.lower()
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """
        Ensure database URL uses async driver.
        
        WHY?
        - Common mistake: postgresql://... (sync)
        - Must be: postgresql+asyncpg://... (async)
        - Catch at startup, not first query!
        """
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use asyncpg driver. "
                "Expected format: postgresql+asyncpg://..."
            )
        return v
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        """
        Parse CORS_ORIGINS from comma-separated string.
        
        WHY?
        - Environment variables are strings
        - .env: CORS_ORIGINS=http://localhost:3000,http://localhost:3001
        - Convert to list automatically
        """
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # ========================================================================
    # COMPUTED PROPERTIES (Derived values)
    # ========================================================================
    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"
    
    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"
    
    @computed_field
    @property
    def database_url_sync(self) -> str:
        """
        Get synchronous database URL (for Alembic migrations).
        
        WHY NEEDED?
        - Alembic migrations don't support async
        - Need sync URL for migrations
        - Convert: postgresql+asyncpg:// → postgresql+psycopg2://
        """
        return self.DATABASE_URL.replace(
            "postgresql+asyncpg://",
            "postgresql+psycopg2://"
        )
    
    @computed_field
    @property
    def log_level(self) -> str:
        """Get appropriate log level for environment."""
        return "DEBUG" if self.is_development else "INFO"
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    def get_cache_key(self, prefix: str, *args: str) -> str:
        """
        Generate cache key with consistent format.
        
        WHY?
        - Consistent key naming across app
        - Easy to find/delete keys by prefix
        
        Example:
            >>> settings.get_cache_key("fires", "pak", "2024-01")
            "geowise:fires:pak:2024-01"
        """
        parts = [self.PROJECT_NAME.lower(), prefix, *args]
        return ":".join(parts)
    
    def create_directories(self) -> None:
        """
        Create required directories if they don't exist.
        
        CALL THIS AT STARTUP (in main.py):
            settings.create_directories()
        """
        for directory in [self.DATA_DIR, self.TILES_DIR, self.CHROMA_DIR]:
            directory.mkdir(parents=True, exist_ok=True)


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================
# WHY SINGLETON?
# - Settings loaded once at import time
# - Same config throughout app lifetime
# - Fast access (no repeated env var lookups)
settings = Settings()

# Validate critical settings at startup
if not settings.NASA_FIRMS_API_KEY and not settings.is_development:
    raise ValueError("NASA_FIRMS_API_KEY required in production")

# Create required directories
settings.create_directories()