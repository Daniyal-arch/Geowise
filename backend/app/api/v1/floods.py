"""
GEOWISE - Floods API Endpoints (v5.2 - OPTIMIZED)
==================================================
FastAPI endpoints for flood detection with on-demand features.

v5.2 ENDPOINTS:
- POST /detect - Fast flood detection (~5-8 sec)
- GET /detect/quick - Simple query version
- GET /statistics - On-demand population/cropland stats
- GET /optical - On-demand optical imagery tiles
- GET /optical/check - Check optical availability
- GET /presets - Available presets
- GET /config/schema - Config parameters for UI

Author: GeoWise AI Team
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any

from app.services.flood_service import flood_service, FloodDetectionConfig
from app.schemas.floods import (
    FloodDetectionRequest,
    FloodDetectionResponse,
    AdminLevelsResponse,
    DistrictListResponse,
    FloodExamplesResponse,
    HealthResponse
)
from app.services.gee_service import gee_service
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


# ============================================================================
# MAIN DETECTION ENDPOINT (FAST)
# ============================================================================

@router.post("/detect", response_model=FloodDetectionResponse)
async def detect_flood(request: FloodDetectionRequest):
    """
    🌊 Universal Flood Detection Endpoint (v5.2 - OPTIMIZED)
    
    FAST response (~5-8 sec) with:
    - Flood extent tiles
    - Flood area (km²)
    - Optical imagery availability
    
    Does NOT include by default (use on-demand endpoints):
    - Population exposure → GET /statistics
    - Cropland/urban impact → GET /statistics
    - Optical imagery → GET /optical
    """
    try:
        logger.info(f"🌊 Flood detection request: {request.location_name or request.bbox}")
        
        # Build config from request
        config = FloodDetectionConfig(
            polarization=request.polarization or "VH+VV",
            diff_threshold_db=request.diff_threshold_db or 2.0
        )
        
        preset = getattr(request, 'preset', None)
        if preset:
            config = FloodDetectionConfig.from_preset(preset)
        
        detection_mode = getattr(request, 'detection_mode', None)
        if detection_mode:
            config.detection_mode = detection_mode
        
        result = await flood_service.detect_flood(
            location_name=request.location_name,
            location_type=request.location_type.value if request.location_type else None,
            country=request.country,
            buffer_km=request.buffer_km,
            bbox=request.bbox,
            coordinates=request.coordinates,
            before_start=str(request.before_start),
            before_end=str(request.before_end),
            after_start=str(request.after_start),
            after_end=str(request.after_end),
            config=config
        )
        
        if result.get('success'):
            stats = result.get('statistics', {})
            if stats:
                logger.info(f"✅ Flood detection complete: {stats.get('flood_area_km2', 0):.2f} km²")
            else:
                logger.info(f"✅ Flood detection complete (overview mode)")
        else:
            logger.warning(f"⚠️ Flood detection failed: {result.get('error')}")
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Flood detection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Flood detection failed: {str(e)}")


@router.get("/detect/quick")
async def detect_flood_quick(
    location: str = Query(..., description="Location name"),
    location_type: str = Query(..., description="Type: country, province, district, river"),
    country: Optional[str] = Query(None, description="Country for disambiguation"),
    before_start: str = Query(..., description="Pre-flood start (YYYY-MM-DD)"),
    before_end: str = Query(..., description="Pre-flood end (YYYY-MM-DD)"),
    after_start: str = Query(..., description="Flood start (YYYY-MM-DD)"),
    after_end: str = Query(..., description="Flood end (YYYY-MM-DD)"),
    buffer_km: Optional[float] = Query(None, description="Buffer for rivers/points"),
    preset: Optional[str] = Query(None, description="Preset: rural_riverine, urban, coastal"),
    threshold_db: Optional[float] = Query(None, ge=0.5, le=10.0, description="Detection threshold (dB)"),
    detection_mode: Optional[str] = Query(None, description="Mode: decrease, increase, bidirectional")
):
    """
    🌊 Quick flood detection via GET request (v5.2)
    
    Returns fast response with flood extent and optical availability.
    For detailed stats, follow up with GET /statistics.
    """
    try:
        if preset:
            config = FloodDetectionConfig.from_preset(preset)
        else:
            config = FloodDetectionConfig()
        
        if threshold_db is not None:
            config.diff_threshold_db = threshold_db
        if detection_mode:
            config.detection_mode = detection_mode
        
        result = await flood_service.detect_flood(
            location_name=location,
            location_type=location_type,
            country=country,
            buffer_km=buffer_km,
            before_start=before_start,
            before_end=before_end,
            after_start=after_start,
            after_end=after_end,
            config=config
        )
        return result
    except Exception as e:
        logger.error(f"Quick flood detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ON-DEMAND: DETAILED STATISTICS
# ============================================================================

@router.get("/statistics")
async def get_detailed_statistics():
    """
    📊 Get detailed flood statistics ON-DEMAND
    
    Returns population exposure, cropland and urban area impact.
    Must be called AFTER a flood detection query (uses cached data).
    
    Trigger phrases: "show statistics", "show population", "show impact"
    """
    try:
        result = flood_service.get_detailed_statistics()
        
        if not result.get('success'):
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'Failed to calculate statistics')
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Statistics calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ON-DEMAND: OPTICAL IMAGERY
# ============================================================================

@router.get("/optical")
async def get_optical_tiles(
    include_ndwi: bool = Query(True, description="Include NDWI layer"),
    include_false_color: bool = Query(True, description="Include false color layer")
):
    """
    🛰️ Get optical imagery tiles ON-DEMAND
    
    Returns Sentinel-2 RGB before/after, false color, and NDWI layers.
    Must be called AFTER a flood detection query (uses cached data).
    
    Trigger phrases: "show optical", "show satellite imagery", "show before/after"
    """
    try:
        result = flood_service.get_optical_tiles(
            include_ndwi=include_ndwi,
            include_false_color=include_false_color
        )
        
        if not result.get('success'):
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'Failed to generate optical tiles')
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Optical tile generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optical/check")
async def check_optical_availability():
    """
    🔍 Check optical imagery availability
    
    Returns availability status without generating tiles.
    Included automatically in flood detection response.
    """
    try:
        if flood_service._last_geometry is None or flood_service._last_query is None:
            raise HTTPException(
                status_code=400,
                detail="No previous flood query found. Run flood detection first."
            )
        
        result = flood_service._check_optical_availability_fast(
            flood_service._last_geometry,
            flood_service._last_query['before_start'],
            flood_service._last_query['before_end'],
            flood_service._last_query['after_start'],
            flood_service._last_query['after_end']
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Optical availability check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PRESET & CONFIG ENDPOINTS
# ============================================================================

@router.get("/presets")
async def get_flood_presets() -> Dict[str, Any]:
    """📋 Get available flood detection presets with their configurations."""
    presets = {
        "rural_riverine": {
            "name": "Rural / Riverine",
            "description": "Optimized for agricultural areas and river floodplains.",
            "config": {
                "polarization": "VH+VV",
                "detection_mode": "decrease",
                "diff_threshold_db": 2.0,
                "permanent_water_threshold": 80,
                "min_connected_pixels": 6
            }
        },
        "urban": {
            "name": "Urban",
            "description": "Bidirectional detection for cities.",
            "config": {
                "polarization": "VH+VV",
                "detection_mode": "bidirectional",
                "diff_threshold_db": 2.0,
                "increase_threshold_db": 2.5,
                "min_connected_pixels": 3
            }
        },
        "coastal": {
            "name": "Coastal",
            "description": "Storm surge and coastal flooding.",
            "config": {
                "polarization": "VV",
                "detection_mode": "decrease",
                "diff_threshold_db": 2.0,
                "permanent_water_threshold": 70
            }
        },
        "flash_flood": {
            "name": "Flash Flood",
            "description": "Rapid onset floods in hilly terrain.",
            "config": {
                "polarization": "VH+VV",
                "detection_mode": "decrease",
                "diff_threshold_db": 1.5,
                "max_slope_deg": 20.0
            }
        },
        "wetland": {
            "name": "Wetland",
            "description": "Shallow flooding in wetland areas.",
            "config": {
                "polarization": "VH",
                "detection_mode": "decrease",
                "diff_threshold_db": 1.5,
                "permanent_water_threshold": 90
            }
        }
    }
    
    return {
        "presets": presets,
        "default": "rural_riverine",
        "validation_note": "rural_riverine preset validated against UNOSAT Pakistan 2022 floods"
    }


@router.get("/config/schema")
async def get_config_schema() -> Dict[str, Any]:
    """📐 Get configuration schema for UI building."""
    return {
        "parameters": {
            "polarization": {
                "type": "enum",
                "options": ["VH", "VV", "VH+VV"],
                "default": "VH+VV",
                "description": "SAR polarization mode"
            },
            "detection_mode": {
                "type": "enum",
                "options": ["decrease", "increase", "bidirectional"],
                "default": "bidirectional",
                "description": "SAR change detection mode"
            },
            "diff_threshold_db": {
                "type": "float",
                "min": 0.5,
                "max": 10.0,
                "default": 2.0,
                "unit": "dB",
                "description": "Threshold for backscatter change detection"
            },
            "permanent_water_threshold": {
                "type": "int",
                "min": 0,
                "max": 100,
                "default": 80,
                "unit": "%",
                "description": "Water occurrence threshold"
            },
            "min_connected_pixels": {
                "type": "int",
                "min": 1,
                "max": 50,
                "default": 4,
                "description": "Minimum connected pixels (noise filter)"
            }
        },
        "on_demand_features": {
            "statistics": {
                "endpoint": "GET /floods/statistics",
                "triggers": ["show statistics", "show population", "show impact"],
                "returns": ["exposed_population", "flooded_cropland_ha", "flooded_urban_ha"]
            },
            "optical": {
                "endpoint": "GET /floods/optical",
                "triggers": ["show optical", "show satellite", "show before/after"],
                "returns": ["optical_before", "optical_after", "false_color_after", "ndwi_after"]
            }
        }
    }


# ============================================================================
# ADMIN BOUNDARY HELPERS
# ============================================================================

@router.get("/admin/{country}", response_model=AdminLevelsResponse)
async def get_admin_levels(country: str):
    """📍 Get available admin divisions for a country."""
    try:
        result = flood_service.get_available_admin_levels(country)
        return result
    except Exception as e:
        logger.error(f"Failed to get admin levels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/districts/{country}/{province}", response_model=DistrictListResponse)
async def get_districts(country: str, province: str):
    """📍 Get list of districts for a province/state."""
    try:
        districts = flood_service.get_districts(country, province)
        return DistrictListResponse(
            country=country,
            province=province,
            districts=districts
        )
    except Exception as e:
        logger.error(f"Failed to get districts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH & INFO ENDPOINTS
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def flood_health_check():
    """🏥 Check flood detection service health."""
    try:
        gee_ok = gee_service.initialized
        
        s1_ok = False
        if gee_ok:
            try:
                import ee
                s1 = ee.ImageCollection('COPERNICUS/S1_GRD').limit(1).size().getInfo()
                s1_ok = s1 > 0
            except:
                pass
        
        status = "healthy" if (gee_ok and s1_ok) else "degraded"
        
        return HealthResponse(
            status=status,
            gee_initialized=gee_ok,
            sentinel1_available=s1_ok,
            message="Flood detection service operational" if status == "healthy" else "Some services unavailable"
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            gee_initialized=False,
            sentinel1_available=False,
            message=str(e)
        )


@router.get("/examples", response_model=FloodExamplesResponse)
async def get_flood_examples():
    """📚 Get example flood detection queries."""
    return FloodExamplesResponse(
        description="Example flood detection requests",
        examples={
            "district_query": {
                "name": "District-level: Dadu, Pakistan (Validated)",
                "request": {
                    "location_name": "Dadu",
                    "location_type": "district",
                    "country": "Pakistan",
                    "before_start": "2022-06-01",
                    "before_end": "2022-07-28",
                    "after_start": "2022-08-15",
                    "after_end": "2022-09-15"
                }
            },
            "province_query": {
                "name": "Province-level: Sindh, Pakistan",
                "request": {
                    "location_name": "Sindh",
                    "location_type": "province",
                    "country": "Pakistan",
                    "before_start": "2022-06-01",
                    "before_end": "2022-07-15",
                    "after_start": "2022-08-25",
                    "after_end": "2022-09-05"
                }
            }
        },
        natural_language_queries=[
            "Show floods in Dadu district August 2022",
            "Detect flooding in Sindh province",
            "Show flood extent in Kerala August 2018"
        ],
        methodology={
            "sensor": "Sentinel-1 SAR (C-band, 10m resolution)",
            "technique": "Change detection (Before vs After flood)",
            "threshold": "Backscatter decrease > 2.0 dB (validated)",
            "refinements": [
                "Permanent water mask (occurrence >= 80%)",
                "Slope filter (<5°)",
                "Connected pixel filter (min 4 pixels)"
            ]
        }
    )