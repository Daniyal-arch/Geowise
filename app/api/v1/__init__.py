"""GEOWISE API v1"""

from fastapi import APIRouter

# Import with error handling
try:
    from app.api.v1 import health, fires, analysis, forest, climate, tiles, query, api
    print("✅ All route modules loaded")
except ImportError as e:
    print(f"❌ Import error: {e}")
    raise

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(fires.router, prefix="/fires", tags=["Fires"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
api_router.include_router(forest.router, prefix="/forest", tags=["Forest"])
api_router.include_router(climate.router, prefix="/climate", tags=["Climate"])
api_router.include_router(tiles.router, prefix="/tiles", tags=["Tiles"])
api_router.include_router(query.router, prefix="/query", tags=["Query"])
api_router.include_router(api.router, prefix="", tags=["Info"])