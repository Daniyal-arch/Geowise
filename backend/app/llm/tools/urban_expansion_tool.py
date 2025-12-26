"""
Urban Expansion Analysis Tool - Google Earth Engine
app/llm/tools/urban_expansion_tool.py
"""

from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
import ee
from datetime import datetime

from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# GHSL EPOCHS AVAILABLE
# ============================================================================

GHSL_EPOCHS = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020]

# ============================================================================
# COLOR PALETTES
# ============================================================================

PALETTES = {
    "neon": [
        '000000', '001a1a', '003333', '004d4d', '006666',
        '008080', '00b3b3', '00e6e6', '00ffff', '80ffff', 'ffffff'
    ],
    "gold": [
        '000000', '1a0f00', '332000', '4d3000', '664000',
        '805000', 'b37300', 'e69500', 'ffaa00', 'ffc44d', 'ffe066'
    ],
    "magma": [
        '000004', '140e36', '3b0f70', '641a80', '8c2981',
        'b73779', 'de4968', 'f7705c', 'fe9f6d', 'fecf92', 'fcfdbf'
    ],
    "timeline": ['2c7bb6', '00a6ca', '90eb9d', 'f9d057', 'd7191c']
}


# ============================================================================
# GEOCODING FALLBACK
# ============================================================================

CITY_LOCATIONS = {
    # Major Cities
    "dubai": {"center": [55.2708, 25.2048], "buffer_km": 40, "country": "UAE"},
    "lahore": {"center": [74.3587, 31.5204], "buffer_km": 30, "country": "Pakistan"},
    "karachi": {"center": [67.0011, 24.8607], "buffer_km": 40, "country": "Pakistan"},
    "islamabad": {"center": [73.0479, 33.6844], "buffer_km": 25, "country": "Pakistan"},
    "mumbai": {"center": [72.8777, 19.0760], "buffer_km": 35, "country": "India"},
    "delhi": {"center": [77.1025, 28.7041], "buffer_km": 40, "country": "India"},
    "beijing": {"center": [116.4074, 39.9042], "buffer_km": 50, "country": "China"},
    "shanghai": {"center": [121.4737, 31.2304], "buffer_km": 50, "country": "China"},
    "tokyo": {"center": [139.6917, 35.6895], "buffer_km": 50, "country": "Japan"},
    "singapore": {"center": [103.8198, 1.3521], "buffer_km": 25, "country": "Singapore"},
    "riyadh": {"center": [46.6753, 24.7136], "buffer_km": 40, "country": "Saudi Arabia"},
    "doha": {"center": [51.5310, 25.2854], "buffer_km": 30, "country": "Qatar"},
    "abu dhabi": {"center": [54.3773, 24.4539], "buffer_km": 35, "country": "UAE"},
    "cairo": {"center": [31.2357, 30.0444], "buffer_km": 40, "country": "Egypt"},
    "lagos": {"center": [3.3792, 6.5244], "buffer_km": 35, "country": "Nigeria"},
    "nairobi": {"center": [36.8219, -1.2921], "buffer_km": 30, "country": "Kenya"},
    "johannesburg": {"center": [28.0473, -26.2041], "buffer_km": 40, "country": "South Africa"},
    "sao paulo": {"center": [-46.6333, -23.5505], "buffer_km": 50, "country": "Brazil"},
    "mexico city": {"center": [-99.1332, 19.4326], "buffer_km": 45, "country": "Mexico"},
    "new york": {"center": [-74.0060, 40.7128], "buffer_km": 40, "country": "USA"},
    "los angeles": {"center": [-118.2437, 34.0522], "buffer_km": 50, "country": "USA"},
    "london": {"center": [-0.1276, 51.5074], "buffer_km": 40, "country": "UK"},
    "paris": {"center": [2.3522, 48.8566], "buffer_km": 35, "country": "France"},
}


def get_city_geometry(city_name: str, buffer_km: Optional[float] = None) -> Optional[Dict]:
    """Get city center and buffer geometry"""
    
    city_key = city_name.lower().strip()
    
    if city_key in CITY_LOCATIONS:
        city_data = CITY_LOCATIONS[city_key]
        buffer = buffer_km or city_data["buffer_km"]
        
        return {
            "center": city_data["center"],
            "buffer_km": buffer,
            "country": city_data["country"],
            "name": city_name.title()
        }
    
    # Try partial match
    for key, data in CITY_LOCATIONS.items():
        if city_key in key or key in city_key:
            buffer = buffer_km or data["buffer_km"]
            return {
                "center": data["center"],
                "buffer_km": buffer,
                "country": data["country"],
                "name": key.title()
            }
    
    return None


# ============================================================================
# MAIN TOOL
# ============================================================================

@tool
def analyze_urban_expansion(
    location_name: str,
    start_year: int = 1975,
    end_year: int = 2020,
    buffer_km: Optional[float] = None,
    palette: str = "neon",
    include_animation: bool = True,
    include_population: bool = True
) -> Dict[str, Any]:
    """
    Analyze urban expansion for a city using GHSL Built-up Surface data.
    
    Args:
        location_name: City name (e.g., "Dubai", "Lahore", "Shanghai")
        start_year: Analysis start year (1975-2020, must be in GHSL epochs)
        end_year: Analysis end year (1975-2020, must be in GHSL epochs)
        buffer_km: Radius around city center in km (default varies by city)
        palette: Color palette ("neon", "gold", "magma")
        include_animation: Generate animation frames
        include_population: Include population data
    
    Returns:
        Dict with tiles, statistics, and animation data
    """
    
    try:
        logger.info(f"🏙️ Urban expansion analysis: {location_name} ({start_year}-{end_year})")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 1: GET LOCATION
        # ═══════════════════════════════════════════════════════════════════
        
        city_data = get_city_geometry(location_name, buffer_km)
        
        if not city_data:
            return {
                "success": False,
                "error": f"City not found: {location_name}",
                "suggestion": f"Available cities: {', '.join(list(CITY_LOCATIONS.keys())[:10])}..."
            }
        
        center = city_data["center"]
        buffer = city_data["buffer_km"]
        
        # Create EE geometry
        center_point = ee.Geometry.Point(center)
        aoi = center_point.buffer(buffer * 1000)  # Convert km to meters
        
        logger.info(f"  📍 Center: {center}, Buffer: {buffer}km")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 2: LOAD GHSL DATA
        # ═══════════════════════════════════════════════════════════════════
        
        ghsl_built = ee.ImageCollection("JRC/GHSL/P2023A/GHS_BUILT_S")
        ghsl_pop = ee.ImageCollection("JRC/GHSL/P2023A/GHS_POP")
        
        # Validate years
        valid_start = min(GHSL_EPOCHS, key=lambda x: abs(x - start_year))
        valid_end = min(GHSL_EPOCHS, key=lambda x: abs(x - end_year))
        
        if valid_start != start_year:
            logger.info(f"  ⚠️ Adjusted start year: {start_year} → {valid_start}")
        if valid_end != end_year:
            logger.info(f"  ⚠️ Adjusted end year: {end_year} → {valid_end}")
        
        # Get built-up images
        def get_built_image(year: int):
            return ghsl_built.filter(
                ee.Filter.eq('system:index', str(year))
            ).first().select('built_surface')
        
        built_start = get_built_image(valid_start)
        built_end = get_built_image(valid_end)
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 3: CALCULATE STATISTICS
        # ═══════════════════════════════════════════════════════════════════
        
        urban_threshold = 500  # sq m per pixel to count as urban
        
        def calculate_urban_area(image, geometry):
            """Calculate urban area in hectares"""
            urban_mask = image.gt(urban_threshold)
            area = urban_mask.multiply(ee.Image.pixelArea()).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=100,
                maxPixels=1e13
            )
            return ee.Number(area.get('built_surface')).divide(10000)  # Convert to hectares
        
        area_start = calculate_urban_area(built_start, aoi).getInfo()
        area_end = calculate_urban_area(built_end, aoi).getInfo()
        
        # Calculate growth metrics
        absolute_growth = area_end - area_start
        growth_percent = ((area_end - area_start) / area_start * 100) if area_start > 0 else 0
        years_diff = valid_end - valid_start
        
        # Annual Compound Growth Rate
        if area_start > 0 and years_diff > 0:
            acgr = ((area_end / area_start) ** (1 / years_diff) - 1) * 100
        else:
            acgr = 0
        
        logger.info(f"  📊 Area {valid_start}: {area_start:.0f} ha → {valid_end}: {area_end:.0f} ha")
        logger.info(f"  📈 Growth: {growth_percent:.1f}% ({acgr:.2f}% annually)")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 4: CREATE URBANIZATION TIMELINE
        # ═══════════════════════════════════════════════════════════════════
        
        # Create "when did each pixel become urban" map
        epochs_in_range = [y for y in GHSL_EPOCHS if valid_start <= y <= valid_end]
        
        urbanization_epoch = ee.Image(0)
        
        for i, year in enumerate(epochs_in_range):
            built_year = get_built_image(year)
            is_urban = built_year.gt(urban_threshold)
            
            if i == 0:
                urbanization_epoch = urbanization_epoch.where(is_urban.eq(1), year)
            else:
                prev_year = epochs_in_range[i - 1]
                built_prev = get_built_image(prev_year)
                was_urban = built_prev.gt(urban_threshold)
                newly_urban = is_urban.eq(1).And(was_urban.eq(0))
                urbanization_epoch = urbanization_epoch.where(newly_urban, year)
        
        urbanization_epoch = urbanization_epoch.selfMask()
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 5: GENERATE TILE URLs
        # ═══════════════════════════════════════════════════════════════════
        
        selected_palette = PALETTES.get(palette, PALETTES["neon"])
        timeline_palette = PALETTES["timeline"]
        
        # Built-up end year visualization
        built_end_vis = built_end.clip(aoi).visualize(
            min=0,
            max=7000,
            palette=selected_palette
        )
        built_end_mapid = built_end_vis.getMapId()
        
        # Urbanization timeline visualization
        timeline_vis = urbanization_epoch.clip(aoi).visualize(
            min=valid_start,
            max=valid_end,
            palette=timeline_palette
        )
        timeline_mapid = timeline_vis.getMapId()
        
        # Growth layer (new urban areas)
        growth_image = built_end.subtract(built_start).gt(urban_threshold).selfMask()
        growth_vis = growth_image.clip(aoi).visualize(palette=['ff0000'])
        growth_mapid = growth_vis.getMapId()
        
        tiles = {
            "built_up": {
                "url": built_end_mapid['tile_fetcher'].url_format,
                "name": f"Built-up {valid_end}",
                "description": f"Urban density in {valid_end}"
            },
            "urbanization_timeline": {
                "url": timeline_mapid['tile_fetcher'].url_format,
                "name": "Urbanization Timeline",
                "description": f"When areas became urban ({valid_start}-{valid_end})"
            },
            "new_urban": {
                "url": growth_mapid['tile_fetcher'].url_format,
                "name": f"New Urban ({valid_start}-{valid_end})",
                "description": "Areas that became urban during analysis period"
            }
        }
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 6: ANIMATION FRAMES (if requested)
        # ═══════════════════════════════════════════════════════════════════
        
        animation_data = None
        
        if include_animation:
            logger.info("  🎬 Generating animation frames...")
            
            animation_frames = []
            
            for year in epochs_in_range:
                built_year = get_built_image(year)
                built_vis = built_year.clip(aoi).visualize(
                    min=0,
                    max=7000,
                    palette=selected_palette
                )
                mapid = built_vis.getMapId()
                
                animation_frames.append({
                    "year": year,
                    "tile_url": mapid['tile_fetcher'].url_format
                })
            
            # Generate GIF URL
            gif_collection = ee.ImageCollection([
                get_built_image(y).clip(aoi).visualize(
                    min=0, max=7000, palette=selected_palette
                )
                for y in epochs_in_range
            ])
            
            gif_params = {
                'region': aoi,
                'dimensions': 600,
                'framesPerSecond': 1.5,
                'crs': 'EPSG:4326'
            }
            
            try:
                gif_url = gif_collection.getVideoThumbURL(gif_params)
            except Exception as e:
                logger.warning(f"  ⚠️ GIF generation failed: {e}")
                gif_url = None
            
            animation_data = {
                "frames": animation_frames,
                "gif_url": gif_url,
                "frame_count": len(animation_frames),
                "years": epochs_in_range
            }
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 7: POPULATION DATA (if requested)
        # ═══════════════════════════════════════════════════════════════════
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 7: POPULATION DATA (if requested) - FIXED
        # ═══════════════════════════════════════════════════════════════════

        population_data = None

        if include_population:
            logger.info("  👥 Fetching population data...")
            
            try:
                # GHSL Population epochs available: 1975, 1990, 2000, 2015, 2020 (different from built-up!)
                pop_epochs = [1975, 1990, 2000, 2015, 2020]
                
                def get_population(year: int):
                    """Get population for a specific year with proper filtering"""
                    
                    # Filter the collection
                    pop_img = ghsl_pop.filter(
                        ee.Filter.eq('system:index', str(year))
                    ).first()
                    
                    if pop_img is None:
                        return None
                    
                    pop = pop_img.select('population_count')
                    
                    # Mask out nodata values (negative values are nodata in GHSL)
                    pop = pop.updateMask(pop.gte(0))
                    
                    total = pop.reduceRegion(
                        reducer=ee.Reducer.sum(),
                        geometry=aoi,
                        scale=100,
                        maxPixels=1e13
                    )
                    
                    return ee.Number(total.get('population_count'))
                
                # Find available population years within our analysis range
                pop_years_available = [y for y in pop_epochs if y >= valid_start and y <= valid_end]
                
                if len(pop_years_available) >= 2:
                    pop_start_year = min(pop_years_available)
                    pop_end_year = max(pop_years_available)
                    
                    pop_start = get_population(pop_start_year)
                    pop_end = get_population(pop_end_year)
                    
                    # Get values
                    pop_start_val = pop_start.getInfo() if pop_start else 0
                    pop_end_val = pop_end.getInfo() if pop_end else 0
                    
                    # Ensure positive values (handle any remaining edge cases)
                    pop_start_val = max(0, pop_start_val) if pop_start_val else 0
                    pop_end_val = max(0, pop_end_val) if pop_end_val else 0
                    
                    # Get urban areas at those years for density calculation
                    area_at_pop_start = area_start  # Approximate
                    area_at_pop_end = area_end
                    
                    # For more accurate density, calculate area at population years if different
                    if pop_start_year != valid_start:
                        try:
                            built_pop_start = get_built_image(pop_start_year)
                            area_at_pop_start = calculate_urban_area(built_pop_start, aoi).getInfo()
                        except:
                            area_at_pop_start = area_start
                    
                    if pop_end_year != valid_end:
                        try:
                            built_pop_end = get_built_image(pop_end_year)
                            area_at_pop_end = calculate_urban_area(built_pop_end, aoi).getInfo()
                        except:
                            area_at_pop_end = area_end
                    
                    # Calculate densities (people per hectare)
                    density_start = pop_start_val / area_at_pop_start if area_at_pop_start > 0 else 0
                    density_end = pop_end_val / area_at_pop_end if area_at_pop_end > 0 else 0
                    
                    # Calculate growth percentage
                    pop_growth_pct = ((pop_end_val - pop_start_val) / pop_start_val * 100) if pop_start_val > 0 else 0
                    
                    population_data = {
                        "start_year": pop_start_year,
                        "end_year": pop_end_year,
                        "population_start": int(pop_start_val),
                        "population_end": int(pop_end_val),
                        "density_start_per_ha": round(density_start, 1),
                        "density_end_per_ha": round(density_end, 1),
                        "population_growth_percent": round(pop_growth_pct, 1)
                    }
                    
                    logger.info(f"  👥 Population: {pop_start_val:,} ({pop_start_year}) → {pop_end_val:,} ({pop_end_year})")
                
                elif len(pop_years_available) == 1:
                    # Only one year available
                    pop_year = pop_years_available[0]
                    pop_val = get_population(pop_year)
                    pop_val = pop_val.getInfo() if pop_val else 0
                    pop_val = max(0, pop_val) if pop_val else 0
                    
                    density = pop_val / area_end if area_end > 0 else 0
                    
                    population_data = {
                        "start_year": pop_year,
                        "end_year": pop_year,
                        "population_start": int(pop_val),
                        "population_end": int(pop_val),
                        "density_start_per_ha": round(density, 1),
                        "density_end_per_ha": round(density, 1),
                        "population_growth_percent": 0.0
                    }
                
                else:
                    logger.warning("  ⚠️ No population data available for this time range")
                    population_data = None
                    
            except Exception as e:
                logger.warning(f"  ⚠️ Population data failed: {e}")
                import traceback
                traceback.print_exc()
                population_data = None
        # ═══════════════════════════════════════════════════════════════════
        # STEP 8: BUILD RESPONSE
        # ═══════════════════════════════════════════════════════════════════
        
        # Calculate zoom level based on buffer
        if buffer > 40:
            zoom = 9
        elif buffer > 25:
            zoom = 10
        elif buffer > 15:
            zoom = 11
        else:
            zoom = 12
        
        result = {
            "success": True,
            "location": {
                "name": city_data["name"],
                "country": city_data["country"],
                "center": center,
                "buffer_km": buffer
            },
            "analysis_period": {
                "start_year": valid_start,
                "end_year": valid_end,
                "years_analyzed": years_diff
            },
            "statistics": {
                "area_start_ha": round(area_start, 2),
                "area_end_ha": round(area_end, 2),
                "absolute_growth_ha": round(absolute_growth, 2),
                "growth_percent": round(growth_percent, 1),
                "annual_growth_rate": round(acgr, 2),
                "growth_multiplier": round(area_end / area_start, 1) if area_start > 0 else 0
            },
            "tiles": tiles,
            "map_config": {
                "center": center,
                "zoom": zoom
            },
            "animation": animation_data,
            "population": population_data,
            "palette": palette,
            "methodology": {
                "data_source": "JRC GHSL P2023A (GHS_BUILT_S)",
                "resolution": "100m",
                "urban_threshold": f"{urban_threshold} sq m built surface per pixel"
            },
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Urban expansion analysis complete for {city_data['name']}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Urban expansion analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


@tool
def get_urban_expansion_animation(
    location_name: str,
    buffer_km: Optional[float] = None,
    palette: str = "neon"
) -> Dict[str, Any]:
    """
    Get animated urban expansion visualization (GIF + frame tiles).
    
    Args:
        location_name: City name
        buffer_km: Radius in km
        palette: Color palette
    
    Returns:
        Animation data with GIF URL and frame tiles
    """
    
    # Use main tool with animation enabled, other features disabled
    result = analyze_urban_expansion.invoke({
        "location_name": location_name,
        "start_year": 1975,
        "end_year": 2020,
        "buffer_km": buffer_km,
        "palette": palette,
        "include_animation": True,
        "include_population": False
    })
    
    if not result.get("success"):
        return result
    
    # Return animation-focused response
    return {
        "success": True,
        "location": result["location"],
        "animation": result["animation"],
        "statistics": result["statistics"],
        "map_config": result["map_config"]
    }