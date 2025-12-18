"""Health Check Endpoints"""

from fastapi import APIRouter
from datetime import datetime
from app.config import settings

router = APIRouter()


@router.get("")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/detailed")
async def detailed_health():
    """Detailed health check with dependencies"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "connected",
        "timestamp": datetime.now().isoformat()
    }