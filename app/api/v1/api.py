"""
GEOWISE API Router Configuration
Main router that includes all API endpoints.
"""
from fastapi import APIRouter

# Create main API router
api_router = APIRouter()

# We'll add these in Phase 6:
# from . import fires, forest, climate, analysis, tiles, query

# api_router.include_router(fires.router, prefix="/fires", tags=["fires"])
# api_router.include_router(forest.router, prefix="/forest", tags=["forest"])
# api_router.include_router(climate.router, prefix="/climate", tags=["climate"])
# api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
# api_router.include_router(tiles.router, prefix="/tiles", tags=["tiles"])
# api_router.include_router(query.router, prefix="/query", tags=["query"])

# Temporary hello endpoint for testing
@api_router.get("/hello")
async def hello_geowise():
    """
    Test endpoint to verify API is working.
    """
    return {
        "message": "🌍 GEOWISE API is running!",
        "status": "Ready for Phase 1 implementation",
        "next_steps": "Implement database models and external services"
    }