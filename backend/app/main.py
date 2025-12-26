"""
GEOWISE FastAPI Application
"""

import os
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
from app.api.v1 import api_router
from app.services.gee_service import initialize_gee_service  # ⭐ ADD THIS

setup_logging(settings.ENVIRONMENT)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup/shutdown"""
    
    logger.info("🚀 Starting GEOWISE API", version=settings.APP_VERSION)
    
    try:
        # Initialize database
        await init_db()
        logger.info("✅ Database initialized")
        
        # ⭐ Initialize Google Earth Engine
        logger.info("Initializing Google Earth Engine...")
        key_file = 'gee-service-account-key.json'
        
        if os.path.exists(key_file):
            gee_initialized = initialize_gee_service(
                key_file=key_file,
                project_id='active-apogee-444711-k5'
            )
            if gee_initialized:
                logger.info("✅ Google Earth Engine initialized!")
            else:
                logger.error("❌ GEE initialization failed")
        else:
            logger.error(f"❌ GEE key file not found: {os.path.abspath(key_file)}")
            
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    logger.info("🛑 Shutting down GEOWISE API")
    
    try:
        await close_db()
        logger.info("✅ Database closed")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Geospatial AI Platform for Environmental Analysis",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_exception_handler(GEOWISEError, geowise_exception_handler)
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error: {exc.errors()}")
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
    
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION
        }
    
    @app.get("/")
    async def root():
        return {
            "message": "Welcome to GEOWISE API",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs"
        }
    
    logger.info("FastAPI application configured")
    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )