"""Map Tile Endpoints - FINAL FIX WITH CORRECT COUNTRY CODES"""

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta
from typing import Optional
import ee

from app.database import get_async_session
from app.core.aggregation import fire_aggregator
from app.core.tile_generator import tile_generator
from app.services.gee_service import gee_service
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/fire-density")
async def get_fire_density_tiles(
    resolution: int = Query(9, ge=5, le=9),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    days: int = Query(7, ge=1, le=30),
    session: AsyncSession = Depends(get_async_session)
):
    """Get fire density as GeoJSON tiles"""
    
    if not start_date or not end_date:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
    
    aggregated = await fire_aggregator.aggregate_by_h3(
        session=session,
        resolution=resolution,
        start_date=start_date,
        end_date=end_date
    )
    
    geojson = tile_generator.aggregate_to_geojson(
        aggregated_data=aggregated,
        properties=["fire_count", "avg_frp", "max_frp"]
    )
    
    return geojson


@router.get("/heatmap")
async def get_heatmap_data(
    resolution: int = Query(9, ge=5, le=9),
    days: int = Query(7, ge=1, le=30),
    session: AsyncSession = Depends(get_async_session)
):
    """Get heatmap data [lat, lon, intensity]"""
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    aggregated = await fire_aggregator.aggregate_by_h3(
        session=session,
        resolution=resolution,
        start_date=start_date,
        end_date=end_date
    )
    
    heatmap = tile_generator.generate_heatmap_data(
        aggregated_data=aggregated,
        value_field="fire_count"
    )
    
    return {
        "type": "heatmap",
        "data": heatmap,
        "metadata": {
            "resolution": resolution,
            "date_range": f"{start_date} to {end_date}",
            "total_points": len(heatmap)
        }
    }


@router.get("/{country_iso}/drivers")
async def get_driver_tiles(
    country_iso: str,
    driver_type: str = Query("all", regex="^(all|permanent_agriculture|hard_commodities|shifting_cultivation|logging|wildfire|settlements|other)$")
):
    """
    Get deforestation driver tiles for a country using WRI/Google DeepMind dataset
    
    Dataset: Global Drivers of Forest Loss 2001-2024 (1km resolution)
    Source: World Resources Institute & Google DeepMind
    
    Args:
        country_iso: 2 or 3-letter ISO country code (BR/BRA, ID/IDN, etc.)
        driver_type: Filter by driver type or 'all' for complete layer
    
    Returns:
        Tile URL and driver category information with 7 driver classes
    """
    try:
        # Validate GEE is initialized
        if not gee_service.initialized:
            raise HTTPException(
                status_code=503,
                detail="Google Earth Engine service not initialized"
            )
        
        country_iso = country_iso.upper()
        
        logger.info(f"[Drivers] Generating tiles for {country_iso}, type: {driver_type}")
        
        # ✅ FIX: Convert 3-letter codes to 2-letter codes for LSIB
        # LSIB uses 2-letter ISO codes (BR, not BRA)
        iso_map = {
            'BRA': 'BR', 'IDN': 'ID', 'COG': 'CG', 'MYS': 'MY',
            'PER': 'PE', 'COL': 'CO', 'PNG': 'PG', 'VNM': 'VN',
            'KHM': 'KH', 'LAO': 'LA', 'THA': 'TH', 'MMR': 'MM',
            'BOL': 'BO', 'VEN': 'VE', 'GUY': 'GY', 'SUR': 'SR',
            'ECU': 'EC', 'PRY': 'PY', 'CHL': 'CL', 'ARG': 'AR',
            'MEX': 'MX', 'GTM': 'GT', 'HND': 'HN', 'NIC': 'NI',
            'CRI': 'CR', 'PAN': 'PA', 'IND': 'IN', 'NPL': 'NP',
            'BGD': 'BD', 'LKA': 'LK', 'PAK': 'PK', 'AFG': 'AF',
            'CHN': 'CN', 'JPN': 'JP', 'KOR': 'KR', 'USA': 'US',
            'CAN': 'CA', 'AUS': 'AU', 'NZL': 'NZ', 'ZAF': 'ZA',
            'KEN': 'KE', 'TZA': 'TZ', 'UGA': 'UG', 'RWA': 'RW',
            'CMR': 'CM', 'GAB': 'GA', 'GHA': 'GH', 'NGA': 'NG',
            'ZMB': 'ZM', 'ZWE': 'ZW', 'MOZ': 'MZ', 'MDG': 'MG'
        }
        
        # Convert to 2-letter code if needed
        if len(country_iso) == 3:
            country_code_2 = iso_map.get(country_iso)
            if not country_code_2:
                raise HTTPException(
                    status_code=400,
                    detail=f"Country code {country_iso} not found. Please use 2-letter codes (BR, ID, etc.) or add to mapping."
                )
        elif len(country_iso) == 2:
            country_code_2 = country_iso
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Country code must be 2 or 3 letters, got: {country_iso}"
            )
        
        logger.info(f"[Drivers] Using country code: {country_code_2}")
        
        # Get country geometry using 2-letter code
        countries = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017')
        country = countries.filter(ee.Filter.eq('country_co', country_code_2))
        
        # Validate country exists
        count = country.size().getInfo()
        if count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Country {country_code_2} ({country_iso}) not found in LSIB dataset"
            )
        
        geometry = country.geometry()
        
        # Load WRI/DeepMind Global Drivers of Forest Loss dataset
        drivers = ee.Image('projects/landandcarbon/assets/wri_gdm_drivers_forest_loss_1km/v1_2_2001_2024')
        
        # Select the classification band (values 1-7)
        drivers_class = drivers.select('classification')
        
        # Clip to country boundary
        drivers_clipped = drivers_class.clip(geometry)
        
        # Filter by driver type if specified
        if driver_type != "all":
            driver_codes = {
                "permanent_agriculture": 1,
                "hard_commodities": 2,
                "shifting_cultivation": 3,
                "logging": 4,
                "wildfire": 5,
                "settlements": 6,
                "other": 7
            }
            code = driver_codes[driver_type]
            drivers_clipped = drivers_clipped.eq(code).selfMask()
        
        # Visualization parameters for 7 driver categories
        driver_vis = {
            'min': 1,
            'max': 7,
            'palette': [
                '#E39D29',  # 1: Permanent agriculture (gold)
                '#E58074',  # 2: Hard commodities/mining (coral)
                '#e9d700',  # 3: Shifting cultivation (yellow)
                '#51a44e',  # 4: Logging (green)
                '#895128',  # 5: Wildfire (brown)
                '#a354a0',  # 6: Settlements & infrastructure (purple)
                '#3a209a'   # 7: Other natural disturbances (dark purple)
            ]
        }
        
        # Generate map tiles
        mapid = drivers_clipped.visualize(**driver_vis).getMapId()
        
        result = {
            "success": True,
            "country_iso": country_iso,
            "country_code": country_code_2,
            "driver_type": driver_type,
            "tile_url": mapid['tile_fetcher'].url_format,
            "driver_categories": {
                1: {
                    "name": "Permanent agriculture",
                    "color": "#E39D29",
                    "description": "Long-term agriculture including crops, pasture, and perennial tree crops"
                },
                2: {
                    "name": "Hard commodities",
                    "color": "#E58074",
                    "description": "Mining and energy infrastructure expansion"
                },
                3: {
                    "name": "Shifting cultivation",
                    "color": "#e9d700",
                    "description": "Temporary cultivation with fallow periods"
                },
                4: {
                    "name": "Logging",
                    "color": "#51a44e",
                    "description": "Timber extraction in natural forests or plantations"
                },
                5: {
                    "name": "Wildfire",
                    "color": "#895128",
                    "description": "Fire-driven tree cover loss"
                },
                6: {
                    "name": "Settlements & infrastructure",
                    "color": "#a354a0",
                    "description": "Urban expansion, roads, and built infrastructure"
                },
                7: {
                    "name": "Other natural disturbances",
                    "color": "#3a209a",
                    "description": "Storms, flooding, landslides, and other natural events"
                }
            },
            "dataset_info": {
                "source": "WRI/Google DeepMind",
                "resolution": "1km",
                "year": "2001-2024",
                "citation": "Global Forest Watch / Land & Carbon Lab",
                "method": "ResNet deep learning model trained on high-resolution imagery",
                "accuracy": "Validated using independent stratified random sampling"
            }
        }
        
        logger.info(f"[Drivers] ✅ Tiles generated successfully for {country_code_2}")
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"[Drivers] Error generating tiles for {country_iso}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate driver tiles: {str(e)}"
        )