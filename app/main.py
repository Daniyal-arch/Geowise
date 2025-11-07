"""
GEOWISE FastAPI Application Entry Point
Main application factory that configures FastAPI with all dependencies.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.utils.logger import setup_logging, get_logger
from app.utils.exceptions import GEOWISEError, geowise_exception_handler
from app.database import init_db, close_db
from app.api.v1.api import api_router

# Setup logging first
logger = get_logger(__name__)
setup_logging(settings.ENVIRONMENT)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.
    
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown")
    
    Why use lifespan?
    - Cleaner async context manager pattern
    - Better error handling during startup/shutdown
    - Proper resource management
    - Newer FastAPI pattern (future-proof)
    """
    # Startup sequence
    logger.info("🚀 Starting GEOWISE API Server", version=settings.APP_VERSION)
    
    try:
        # Initialize database connection pool
        await init_db()
        logger.info("✅ Database connection pool initialized")
        
        # Future: Initialize cache, external service connections, etc.
        logger.info("✅ All services initialized")
        
    except Exception as e:
        logger.error("❌ Startup failed", error=str(e))
        raise
    
    # Application runs here
    yield
    
    # Shutdown sequence
    logger.info("🛑 Shutting down GEOWISE API Server")
    
    try:
        # Close database connections
        await close_db()
        logger.info("✅ Database connections closed")
        
        # Future: Close other resources
        logger.info("✅ All resources cleaned up")
        
    except Exception as e:
        logger.error("❌ Shutdown error", error=str(e))


def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
        
    Why use factory pattern?
    - Easier testing (create multiple app instances)
    - Configuration flexibility
    - Clean separation of app creation and configuration
    """
    # Create FastAPI app with metadata
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
        🌍 GEOWISE API - Geospatial Intelligence for World Environmental Systems & Exploration
        
        A geospatial AI platform that integrates multiple environmental datasets
        (NASA FIRMS fires, Global Forest Watch, Open-Meteo climate, World Bank statistics)
        to perform spatial correlation analysis and generate insights.
        
        ## Key Features
        - Multi-resolution spatial analysis using H3 hexagonal binning
        - Dynamic map tile generation
        - Statistical correlation between environmental variables
        - LLM-powered natural language queries with RAG
        - Real-time and historical data integration
        """,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan  # Use our lifespan context manager
    )
    
    # Configure CORS middleware
    # Why CORS? Frontend (React) runs on different port than backend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],  # Allow all HTTP methods
        allow_headers=["*"],  # Allow all headers
    )
    
    # Add custom exception handlers
    app.add_exception_handler(GEOWISEError, geowise_exception_handler)
    
    # Add validation error handler
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Custom handler for request validation errors.
        
        Provides more structured error responses than default.
        """
        logger.warning(
            "Request validation failed",
            path=request.url.path,
            errors=exc.errors(),
            body=exc.body
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": exc.errors()
                }
            }
        )
    
    # Include API routers
    # Note: We'll create these in Phase 6, but the structure is ready
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Health check endpoint
    # Essential for deployment and monitoring
    @app.get("/health")
    async def health_check():
        """
        Health check endpoint for load balancers and monitoring.
        
        Returns:
            Simple status indicating API health
        """
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT
        }
    
    # Root endpoint
    @app.get("/")
    async def root():
        """
        Root endpoint with API information.
        """
        return {
            "message": "Welcome to GEOWISE API",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/health"
        }
    
    # Log application startup configuration
    logger.info(
        "FastAPI application configured",
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        cors_origins=settings.BACKEND_CORS_ORIGINS
    )
    
    return app


# Create the application instance
# This is what uvicorn will run
app = create_application()


# Development convenience
if __name__ == "__main__":
    """
    Run with: python -m app.main
    Useful for debugging without uvicorn
    """
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,  # Auto-reload in development
        log_level="info"
    )