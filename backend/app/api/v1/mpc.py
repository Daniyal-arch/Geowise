"""
Microsoft Planetary Computer (MPC) Query Endpoint
On-demand land use data retrieval from MPC STAC API
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import requests
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
import planetary_computer as pc
import numpy as np

from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class MPCQueryRequest(BaseModel):
    """MPC query request schema"""
    bbox: List[float] = Field(
        ..., 
        min_items=4, 
        max_items=4,
        description="Bounding box [west, south, east, north] in EPSG:4326"
    )
    year: int = Field(..., ge=2017, le=2023, description="Year for land use data (2017-2023)")
    region_name: str = Field("Custom Region", description="Human-readable region name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "bbox": [-75.0, -15.0, -45.0, 5.0],
                "year": 2020,
                "region_name": "Amazon Basin"
            }
        }


class LandUseClass(BaseModel):
    """Land use classification with pixel count and percentage"""
    class_id: int
    class_name: str
    pixel_count: int
    percentage: float
    color: str  # Hex color for visualization


class MPCQueryResponse(BaseModel):
    """MPC query response schema"""
    status: str
    region: str
    year: int
    bbox: List[float]
    land_use_classes: List[LandUseClass]
    total_pixels: int
    resolution: str
    source: str
    item_id: str
    metadata: Dict[str, Any]


# ============================================================================
# LAND USE CLASS DEFINITIONS (ESA WorldCover)
# ============================================================================

LAND_USE_CLASSES = {
    10: {"name": "Tree cover", "color": "#006400"},
    20: {"name": "Shrubland", "color": "#FFBB22"},
    30: {"name": "Grassland", "color": "#FFFF4C"},
    40: {"name": "Cropland", "color": "#F096FF"},
    50: {"name": "Built-up", "color": "#FA0000"},
    60: {"name": "Bare / sparse vegetation", "color": "#B4B4B4"},
    70: {"name": "Snow and ice", "color": "#F0F0F0"},
    80: {"name": "Permanent water bodies", "color": "#0064C8"},
    90: {"name": "Herbaceous wetland", "color": "#0096A0"},
    95: {"name": "Mangroves", "color": "#00CF75"},
    100: {"name": "Moss and lichen", "color": "#FAE6A0"}
}


# ============================================================================
# MPC QUERY LOGIC
# ============================================================================

def query_mpc_stac(bbox: List[float], year: int) -> Optional[Dict[str, Any]]:
    """
    Query MPC STAC API for land use data
    
    Args:
        bbox: [west, south, east, north]
        year: Year for data (2017-2023)
    
    Returns:
        Signed STAC item or None if not found
    """
    try:
        stac_url = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
        
        search_params = {
            "collections": ["io-lulc-annual-v02"],  # ESA WorldCover 10m
            "bbox": bbox,
            "datetime": f"{year}-01-01/{year}-12-31",
            "limit": 5
        }
        
        logger.info(f"Querying MPC STAC: {search_params}")
        
        response = requests.post(stac_url, json=search_params, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"MPC STAC query failed: {response.status_code}")
            return None
        
        items = response.json().get('features', [])
        
        if not items:
            logger.warning(f"No MPC items found for bbox={bbox}, year={year}")
            return None
        
        # Sign the first item with Planetary Computer credentials
        signed_item = pc.sign(items[0])
        logger.info(f"Found MPC item: {signed_item.get('id')}")
        
        return signed_item
        
    except Exception as e:
        logger.error(f"MPC STAC query error: {e}")
        return None


def extract_land_use_data(signed_item: Dict[str, Any], bbox: List[float]) -> Optional[Dict[str, Any]]:
    """
    Extract land use data from MPC raster tile
    
    Args:
        signed_item: Signed STAC item
        bbox: [west, south, east, north]
    
    Returns:
        Dict with land use statistics or None
    """
    try:
        data_url = signed_item['assets']['data']['href']
        
        with rasterio.open(data_url) as src:
            # Transform bbox to raster CRS
            west, south, east, north = bbox
            transformed = transform_bounds('EPSG:4326', src.crs, west, south, east, north)
            
            # Check overlap
            bounds = src.bounds
            overlap_west = max(transformed[0], bounds.left)
            overlap_south = max(transformed[1], bounds.bottom)
            overlap_east = min(transformed[2], bounds.right)
            overlap_north = min(transformed[3], bounds.top)
            
            if overlap_west >= overlap_east or overlap_south >= overlap_north:
                logger.warning("No overlap between query bbox and raster")
                return None
            
            # Calculate window
            window = from_bounds(
                overlap_west, overlap_south, overlap_east, overlap_north,
                src.transform
            )
            
            # Limit window size to prevent memory issues
            max_pixels = 1_000_000  # 1M pixels max
            if window.width * window.height > max_pixels:
                scale = np.sqrt(max_pixels / (window.width * window.height))
                window = rasterio.windows.Window(
                    window.col_off, window.row_off,
                    int(window.width * scale),
                    int(window.height * scale)
                )
            
            # Read data
            data = src.read(1, window=window)
            
            if data.size == 0:
                logger.warning("Empty raster data")
                return None
            
            # Calculate class distribution
            unique, counts = np.unique(data, return_counts=True)
            total_pixels = data.size
            
            class_distribution = []
            for class_id, count in zip(unique, counts):
                class_info = LAND_USE_CLASSES.get(int(class_id))
                if class_info:
                    class_distribution.append({
                        "class_id": int(class_id),
                        "class_name": class_info["name"],
                        "pixel_count": int(count),
                        "percentage": round((count / total_pixels) * 100, 2),
                        "color": class_info["color"]
                    })
            
            # Sort by percentage (descending)
            class_distribution.sort(key=lambda x: x["percentage"], reverse=True)
            
            return {
                "classes": class_distribution,
                "total_pixels": int(total_pixels),
                "resolution": "10m",
                "item_id": signed_item.get('id')
            }
            
    except Exception as e:
        logger.error(f"MPC data extraction error: {e}")
        return None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/query", response_model=MPCQueryResponse)
async def query_mpc_land_use(request: MPCQueryRequest):
    """
    🗺️ Query Microsoft Planetary Computer for Land Use Data
    
    Retrieves ESA WorldCover 10m resolution land use classification for a given region.
    
    **Available Years**: 2017-2023 (2020, 2021 recommended for best coverage)
    
    **Land Use Classes**:
    - Tree cover (10)
    - Shrubland (20)
    - Grassland (30)
    - Cropland (40)
    - Built-up (50)
    - Bare/sparse vegetation (60)
    - Snow and ice (70)
    - Water bodies (80)
    - Wetland (90)
    - Mangroves (95)
    - Moss and lichen (100)
    
    **Example Request**:
    ```json
    {
      "bbox": [-60.0, -5.0, -55.0, 0.0],
      "year": 2020,
      "region_name": "Amazon Rainforest"
    }
    ```
    
    **Response**: Land use classification with pixel counts and percentages
    """
    
    logger.info(f"MPC query: region={request.region_name}, year={request.year}, bbox={request.bbox}")
    
    # Validate bbox
    west, south, east, north = request.bbox
    if west >= east or south >= north:
        raise HTTPException(
            status_code=400,
            detail="Invalid bounding box: west must be < east, south must be < north"
        )
    
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= 90 and -90 <= north <= 90):
        raise HTTPException(
            status_code=400,
            detail="Bounding box coordinates out of range"
        )
    
    # Query MPC STAC
    signed_item = query_mpc_stac(request.bbox, request.year)
    
    if not signed_item:
        raise HTTPException(
            status_code=404,
            detail=f"No MPC data available for region {request.region_name} in {request.year}. "
                   f"MPC coverage may not include this area. Try a different region or year."
        )
    
    # Extract land use data
    land_use_data = extract_land_use_data(signed_item, request.bbox)
    
    if not land_use_data:
        raise HTTPException(
            status_code=500,
            detail="Failed to extract land use data from MPC raster"
        )
    
    # Build response
    response = MPCQueryResponse(
        status="success",
        region=request.region_name,
        year=request.year,
        bbox=request.bbox,
        land_use_classes=[LandUseClass(**cls) for cls in land_use_data["classes"]],
        total_pixels=land_use_data["total_pixels"],
        resolution=land_use_data["resolution"],
        source="Microsoft Planetary Computer - ESA WorldCover",
        item_id=land_use_data["item_id"],
        metadata={
            "collection": "io-lulc-annual-v02",
            "spatial_resolution": "10m",
            "temporal_resolution": "annual",
            "coordinate_system": "EPSG:4326"
        }
    )
    
    logger.info(f"MPC query successful: {len(land_use_data['classes'])} classes found")
    
    return response


@router.get("/coverage")
async def get_mpc_coverage():
    """
    📍 Get MPC Data Coverage Information
    
    Returns information about available data coverage in MPC.
    """
    
    return {
        "status": "available",
        "collection": "io-lulc-annual-v02",
        "description": "ESA WorldCover 10m Annual Land Use Classification",
        "years_available": [2017, 2018, 2019, 2020, 2021, 2022, 2023],
        "recommended_years": [2020, 2021],
        "spatial_resolution": "10m",
        "coordinate_system": "EPSG:4326",
        "global_coverage": "Yes",
        "land_use_classes": [
            {"id": 10, "name": "Tree cover", "color": "#006400"},
            {"id": 20, "name": "Shrubland", "color": "#FFBB22"},
            {"id": 30, "name": "Grassland", "color": "#FFFF4C"},
            {"id": 40, "name": "Cropland", "color": "#F096FF"},
            {"id": 50, "name": "Built-up", "color": "#FA0000"},
            {"id": 60, "name": "Bare/sparse vegetation", "color": "#B4B4B4"},
            {"id": 70, "name": "Snow and ice", "color": "#F0F0F0"},
            {"id": 80, "name": "Water bodies", "color": "#0064C8"},
            {"id": 90, "name": "Herbaceous wetland", "color": "#0096A0"},
            {"id": 95, "name": "Mangroves", "color": "#00CF75"},
            {"id": 100, "name": "Moss and lichen", "color": "#FAE6A0"}
        ],
        "notes": [
            "Best coverage for Amazon, Southeast Asia, Africa",
            "May have gaps in extreme latitudes",
            "2020-2021 have most complete global coverage"
        ]
    }


@router.get("/health")
async def mpc_health_check():
    """Check MPC service availability"""
    
    try:
        # Test STAC API connectivity
        response = requests.get(
            "https://planetarycomputer.microsoft.com/api/stac/v1/",
            timeout=10
        )
        
        if response.status_code == 200:
            return {
                "status": "healthy",
                "service": "Microsoft Planetary Computer",
                "stac_api": "accessible",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "degraded",
                "service": "Microsoft Planetary Computer",
                "stac_api": "error",
                "status_code": response.status_code
            }
            
    except Exception as e:
        logger.error(f"MPC health check failed: {e}")
        return {
            "status": "unavailable",
            "service": "Microsoft Planetary Computer",
            "error": str(e)
        }