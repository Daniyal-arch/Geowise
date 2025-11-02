# backend/app/main.py
"""
FastAPI application entry point for GEOWISE.

WHY FASTAPI?
------------
1. Async by default (non-blocking I/O for external APIs)
2. Automatic OpenAPI docs (Swagger UI at /docs)
3. Type validation (Pydantic)
4. Fast (one of the fastest Python frameworks)
5. Modern Python (3.11+ features, async/await)

ARCHITECTURE:
-------------
- Dependency Injection (database sessions, auth)
- Middleware (CORS, logging, request tracking)
- Exception handlers (consistent error responses)
- Startup/shutdown events (DB initialization)
- API versioning (/api/v1/...)

STARTUP FLOW:
-------------
1. Load configuration (.env → settings)
2. Initialize logger
3. Create FastAPI app
4. Add middleware (CORS, request tracking)
5. Register exception handlers
6. Register routes (/api/v1/fires, etc.)
7. Startup event: Initialize database
8. Ready to serve requests!
"""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import settings
from app.database import init_db, close_db, check_db_health
from app.utils.logger import setup_logging, set_request_id
from app.utils.exceptions import register_exception_handlers


# ============================================================================
# LIFESPAN CONTEXT MANAGER
# ============================================================================
# WHY LIFESPAN?
# - Modern FastAPI pattern (replaces @app.on_event)
# - Better async support
# - Resource cleanup guaranteed
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Manage application lifecycle (startup and shutdown).
    
    WHAT HAPPENS HERE:
    ------------------
    Code BEFORE yield:  Runs at startup
    Code AFTER yield:   Runs at shutdown
    
    WHY ASYNC CONTEXT MANAGER?
    - Ensures cleanup even if startup fails
    - Proper async resource management
    - FastAPI best practice
    """
    
    # ========================================================================
    # STARTUP
    # ========================================================================
    logger.info("=" * 80)
    logger.info(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"   Environment: {settings.ENVIRONMENT}")
    logger.info(f"   Debug mode: {settings.DEBUG}")
    logger.info("=" * 80)
    
    try:
        # Initialize database
        await init_db()
        
        # Health check
        db_healthy = await check_db_health()
        if db_healthy:
            logger.success("✅ Database connection established")
        else:
            logger.warning("⚠️  Database health check failed")
        
        # Log available routes
        logger.info("📋 Registered routes:")
        for route in app.routes:
            if hasattr(route, "methods"):
                methods = ", ".join(route.methods)
                logger.info(f"   {methods:6} {route.path}")
        
        logger.success("✅ Application startup complete")
        
    except Exception as e:
        logger.exception(f"❌ Startup failed: {e}")
        raise
    
    # ========================================================================
    # APPLICATION RUNNING
    # ========================================================================
    yield  # App runs here
    
    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    logger.info("🛑 Shutting down application...")
    
    try:
        await close_db()
        logger.success("✅ Application shutdown complete")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")


# ============================================================================
# CREATE FASTAPI APP
# ============================================================================
def create_application() -> FastAPI:
    """
    Factory function to create FastAPI application.
    
    WHY FACTORY PATTERN?
    - Easy to create multiple apps (testing, different configs)
    - Clear initialization order
    - Can pass different settings
    
    Returns:
        FastAPI: Configured application
    """
    
    # ========================================================================
    # APP INITIALIZATION
    # ========================================================================
    app = FastAPI(
        # Basic info (appears in OpenAPI docs)
        title=settings.PROJECT_NAME,
        description="""
        🌍 GEOWISE - Geospatial Intelligence for World Environmental Systems & Exploration
        
        **Progressive Disclosure Environmental Analysis Platform**
        
        Features:
        - 🔥 NASA FIRMS fire data integration
        - 🌲 Global Forest Watch deforestation tracking
        - 🌡️  Open-Meteo climate data
        - 📊 Multi-resolution spatial correlation analysis
        - 🗺️  Dynamic tile server for map visualization
        - 🤖 LLM-powered natural language queries
        
        **API Workflow:**
        1. Fetch individual datasets (fires, forest, climate)
        2. Visualize each dataset independently
        3. Trigger correlation analysis on demand
        4. Generate insights via LLM agents
        """,
        version=settings.VERSION,
        
        # OpenAPI docs configuration
        docs_url="/docs" if settings.is_development else None,  # Disable in prod
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        
        # Lifespan management
        lifespan=lifespan,
        
        # Debug mode
        debug=settings.DEBUG,
    )
    
    # ========================================================================
    # MIDDLEWARE (Order matters! First added = last executed)
    # ========================================================================
    
    # Request tracking middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """
        Add unique request ID for tracing.
        
        WHY?
        - Track single request across multiple log entries
        - Essential for debugging distributed systems
        - Added to response headers for client tracking
        
        FLOW:
        1. Generate UUID for request
        2. Store in context (thread-safe)
        3. Process request
        4. Add to response headers
        """
        request_id = str(uuid.uuid4())
        set_request_id(request_id)
        
        logger.bind(request_id=request_id).info(
            f"➡️  {request.method} {request.url.path}"
        )
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        logger.bind(request_id=request_id).info(
            f"⬅️  {response.status_code}"
        )
        
        return response
    
    # CORS middleware (MUST be last - executes first!)
    # WHY CORS?
    # - Browser security: frontend (localhost:3000) → backend (localhost:8000)
    # - Must explicitly allow origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],  # Allow all HTTP methods
        allow_headers=["*"],  # Allow all headers
        expose_headers=["X-Request-ID"],  # Expose our custom header
    )
    
    # ========================================================================
    # EXCEPTION HANDLERS
    # ========================================================================
    register_exception_handlers(app)
    
    # ========================================================================
    # ROUTES (Will add in Phase 6)
    # ========================================================================
    # TODO: These imports will be uncommented when routes are implemented
    # from app.api.v1.fires import router as fires_router
    # from app.api.v1.forest import router as forest_router
    # from app.api.v1.climate import router as climate_router
    # from app.api.v1.analysis import router as analysis_router
    # from app.api.v1.tiles import router as tiles_router
    # from app.api.v1.query import router as query_router
    
    # app.include_router(fires_router, prefix=f"{settings.API_V1_PREFIX}/fires")
    # app.include_router(forest_router, prefix=f"{settings.API_V1_PREFIX}/forest")
    # app.include_router(climate_router, prefix=f"{settings.API_V1_PREFIX}/climate")
    # app.include_router(analysis_router, prefix=f"{settings.API_V1_PREFIX}/analysis")
    # app.include_router(tiles_router, prefix=f"{settings.API_V1_PREFIX}/tiles")
    # app.include_router(query_router, prefix=f"{settings.API_V1_PREFIX}/query")
    
    return app


# ============================================================================
# BASIC ROUTES (For testing Phase 1)
# ============================================================================
app = create_application()


@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> dict:
    """
    Root endpoint (health check).
    
    WHY?
    - Quick way to check if API is running
    - Shows API version
    - Useful for load balancers
    
    Returns:
        dict: API information
    """
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "docs": f"{settings.API_V1_PREFIX}/docs" if settings.is_development else None,
    }


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """
    Comprehensive health check endpoint.
    
    WHY SEPARATE FROM ROOT?
    - Root: Simple "is it running?"
    - Health: Detailed dependency status
    - Used by monitoring systems (Kubernetes, etc.)
    
    CHECKS:
    - Database connectivity
    - Required extensions (PostGIS, H3)
    - Can return 503 if unhealthy (monitoring alert)
    
    Returns:
        dict: Health status
    """
    
    db_healthy = await check_db_health()
    
    response = {
        "status": "healthy" if db_healthy else "unhealthy",
        "components": {
            "database": "ok" if db_healthy else "error",
            "api": "ok",
        }
    }
    
    # If database down, return 503 (Service Unavailable)
    # WHY 503?
    # - Tells load balancer to route traffic elsewhere
    # - Monitoring systems can detect and alert
    # - Different from 500 (Internal Server Error)
    if not db_healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response
        )
    
    return response


@app.get(f"{settings.API_V1_PREFIX}/info", status_code=status.HTTP_200_OK)
async def api_info() -> dict:
    """
    API information endpoint.
    
    WHY?
    - Shows what's available
    - Configuration status
    - External API availability
    
    Returns:
        dict: API configuration
    """
    return {
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "features": {
            "fires": bool(settings.NASA_FIRMS_API_KEY),
            "forest": True,  # GFW tile servers (no key needed)
            "climate": True,  # Open-Meteo (no key needed)
            "llm": bool(settings.GROQ_API_KEY),
        },
        "spatial": {
            "display_resolution": settings.H3_RESOLUTION_DISPLAY,
            "analysis_resolution": settings.H3_RESOLUTION_ANALYSIS,
        },
        "cache": {
            "enabled": True,
            "tiles_ttl": settings.CACHE_TTL_TILES,
            "fires_ttl": settings.CACHE_TTL_FIRES,
            "analysis_ttl": settings.CACHE_TTL_ANALYSIS,
        }
    }


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    """
    Run the application directly (development only).
    
    HOW TO RUN:
    -----------
    PS> python backend/app/main.py
    
    This starts uvicorn server with auto-reload.
    
    PRODUCTION:
    -----------
    Use uvicorn directly:
    PS> uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    """
    
    import uvicorn
    
    # Setup logging first!
    setup_logging()
    
    logger.info("🚀 Starting uvicorn server...")
    logger.info("📖 API docs will be available at: http://localhost:8000/docs")
    logger.info("🔍 Health check at: http://localhost:8000/health")
    
    uvicorn.run(
        "app.main:app",  # Import path
        host="0.0.0.0",  # Listen on all interfaces
        port=8000,
        reload=True,  # Auto-reload on code changes (dev only!)
        log_level="info",
    )