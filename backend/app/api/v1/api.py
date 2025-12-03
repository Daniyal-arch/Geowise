"""Legacy API compatibility (if needed)"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/info")
async def api_info():
    """API information endpoint"""
    return {
        "api_version": "v1",
        "endpoints": {
            "fires": "/api/v1/fires",
            "analysis": "/api/v1/analysis",
            "forest": "/api/v1/forest",
            "climate": "/api/v1/climate",
            "tiles": "/api/v1/tiles",
            "health": "/api/v1/health"
        },
        "documentation": "/docs"
    }