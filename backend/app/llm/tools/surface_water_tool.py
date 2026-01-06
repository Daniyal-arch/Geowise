"""
Surface Water Change Analysis Tool - Google Earth Engine
app/llm/tools/surface_water_tool.py

Analyzes surface water changes using JRC Global Surface Water dataset.
Supports ANY water body worldwide using:
1. HydroLAKES dataset (1.4M lakes with polygon boundaries)
2. Known water bodies cache (famous lakes with predefined bounds)
3. Geocoding fallback + JRC max_extent boundary detection
"""

from typing import Dict, Any, List, Optional, Tuple
from langchain_core.tools import tool
import ee
import requests
from datetime import datetime

from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# HYDROLAKES DATASET (Earth Engine)
# ============================================================================

HYDROLAKES_COLLECTION = 'projects/sat-io/open-datasets/HydroLakes/lake_poly_v10'


# ============================================================================
# KNOWN WATER BODIES CACHE (Famous lakes with predefined bounds)
# Used as fallback if HydroLAKES search fails
# ============================================================================

KNOWN_WATER_BODIES = {
    # Dramatic shrinking lakes
    "aral sea": {
        "bounds": [57.0, 43.0, 62.0, 47.0],
        "country": "Kazakhstan/Uzbekistan",
        "type": "lake",
        "description": "Once world's 4th largest lake, now 10% of original size"
    },
    "lake chad": {
        "bounds": [12.5, 11.5, 15.5, 14.5],
        "country": "Chad/Nigeria/Niger/Cameroon",
        "type": "lake",
        "description": "Shrunk by 90% since 1960s"
    },
    "lake urmia": {
        "bounds": [44.5, 37.0, 46.5, 38.5],
        "country": "Iran",
        "type": "lake",
        "description": "Iran's largest lake, critically endangered"
    },
    "dead sea": {
        "bounds": [35.3, 31.0, 35.7, 31.8],
        "country": "Israel/Jordan",
        "type": "lake",
        "description": "Lowest point on Earth, shrinking 1m/year"
    },
    "lake poopo": {
        "bounds": [-67.5, -19.5, -66.5, -18.5],
        "country": "Bolivia",
        "type": "lake",
        "description": "Dried up completely in 2015"
    },
    
    # Reservoirs
    "lake mead": {
        "bounds": [-115.0, 35.8, -114.0, 36.6],
        "country": "USA",
        "type": "reservoir",
        "description": "Largest US reservoir, severe drought impact"
    },
    "lake powell": {
        "bounds": [-111.5, 36.5, -110.0, 37.5],
        "country": "USA",
        "type": "reservoir",
        "description": "Second largest US reservoir"
    },
    "three gorges": {
        "bounds": [110.0, 30.0, 112.0, 31.5],
        "country": "China",
        "type": "reservoir",
        "description": "World's largest hydroelectric dam"
    },
    "lake nasser": {
        "bounds": [31.5, 22.0, 33.5, 24.0],
        "country": "Egypt/Sudan",
        "type": "reservoir",
        "description": "Aswan Dam reservoir"
    },
    
    # Deltas
    "indus delta": {
        "bounds": [67.0, 23.5, 68.5, 25.0],
        "country": "Pakistan",
        "type": "delta",
        "description": "Shrinking due to upstream water use"
    },
    "ganges delta": {
        "bounds": [88.0, 21.5, 92.0, 24.0],
        "country": "Bangladesh/India",
        "type": "delta",
        "description": "World's largest delta"
    },
    "mekong delta": {
        "bounds": [105.0, 9.0, 107.0, 11.0],
        "country": "Vietnam",
        "type": "delta",
        "description": "Threatened by sea level rise"
    },
    
    # Other significant lakes
    "lake balkhash": {
        "bounds": [73.0, 45.0, 79.0, 47.5],
        "country": "Kazakhstan",
        "type": "lake",
        "description": "Half fresh, half saline"
    },
    "lake turkana": {
        "bounds": [35.5, 2.5, 37.0, 4.5],
        "country": "Kenya/Ethiopia",
        "type": "lake",
        "description": "World's largest desert lake"
    },
    "lake titicaca": {
        "bounds": [-70.5, -16.5, -68.5, -15.0],
        "country": "Peru/Bolivia",
        "type": "lake",
        "description": "World's highest navigable lake"
    },
    "caspian sea": {
        "bounds": [46.0, 36.5, 54.5, 47.0],
        "country": "Multiple",
        "type": "lake",
        "description": "World's largest enclosed water body"
    },
    "lake victoria": {
        "bounds": [31.5, -3.0, 35.0, 0.5],
        "country": "Kenya/Uganda/Tanzania",
        "type": "lake",
        "description": "Africa's largest lake"
    },
    "salton sea": {
        "bounds": [-116.2, 33.0, -115.4, 33.6],
        "country": "USA",
        "type": "lake",
        "description": "Shrinking saline lake in California"
    },
    "lake tanganyika": {
        "bounds": [29.0, -8.8, 31.2, -3.3],
        "country": "Tanzania/DRC/Burundi/Zambia",
        "type": "lake",
        "description": "World's longest freshwater lake"
    },
    "lake baikal": {
        "bounds": [103.5, 51.4, 110.0, 55.8],
        "country": "Russia",
        "type": "lake",
        "description": "World's deepest and oldest lake"
    },
}


# ============================================================================
# COLOR PALETTES
# ============================================================================

PALETTES = {
    "water_occurrence": [
        'ffffff', 'f0f9ff', 'd4edfc', 'a8dadc', '7ecce5',
        '57b8d4', '3a9fc2', '2182b0', '0a6699', '004c80',
        '003366', '001a33'
    ],
    "water_blue": ['00a8ff'],
    "lost_water": ['ff3333'],
    "new_water": ['33ff33'],
    "max_extent": ['ffcccc'],
}


# ============================================================================
# WATER BODY DETECTION FUNCTIONS
# ============================================================================

def search_hydrolakes(name: str) -> Optional[Dict]:
    """
    Search HydroLAKES dataset for a lake by name.
    Returns lake geometry and metadata if found.
    
    HydroLAKES contains 1.4 million lakes worldwide with polygon boundaries.
    """
    try:
        logger.info(f"  🔍 Searching HydroLAKES for: {name}")
        
        hydro_lakes = ee.FeatureCollection(HYDROLAKES_COLLECTION)
        
        # Search by lake name (case-insensitive partial match)
        # HydroLAKES has 'Lake_name' field
        matched = hydro_lakes.filter(
            ee.Filter.stringContains('Lake_name', name.title())
        )
        
        # Get count
        count = matched.size().getInfo()
        
        if count == 0:
            # Try lowercase
            matched = hydro_lakes.filter(
                ee.Filter.stringContains('Lake_name', name.lower())
            )
            count = matched.size().getInfo()
        
        if count == 0:
            # Try uppercase
            matched = hydro_lakes.filter(
                ee.Filter.stringContains('Lake_name', name.upper())
            )
            count = matched.size().getInfo()
        
        if count > 0:
            # Get the largest matching lake (by area)
            lake = matched.sort('Lake_area', False).first()
            
            # Get properties
            props = lake.toDictionary().getInfo()
            geometry = lake.geometry()
            bounds = geometry.bounds().coordinates().getInfo()[0]
            
            # Extract bounding box [west, south, east, north]
            lons = [coord[0] for coord in bounds]
            lats = [coord[1] for coord in bounds]
            bbox = [min(lons), min(lats), max(lons), max(lats)]
            
            # Add buffer (10% of size)
            lon_buffer = (bbox[2] - bbox[0]) * 0.1
            lat_buffer = (bbox[3] - bbox[1]) * 0.1
            bbox = [
                bbox[0] - lon_buffer,
                bbox[1] - lat_buffer,
                bbox[2] + lon_buffer,
                bbox[3] + lat_buffer
            ]
            
            logger.info(f"  ✅ Found in HydroLAKES: {props.get('Lake_name', name)}")
            logger.info(f"     Country: {props.get('Country', 'Unknown')}")
            logger.info(f"     Area: {props.get('Lake_area', 0):.0f} km²")
            
            return {
                "name": props.get('Lake_name', name.title()),
                "country": props.get('Country', 'Unknown'),
                "type": "lake",
                "bounds": bbox,
                "area_km2": props.get('Lake_area', 0),
                "volume_km3": props.get('Vol_total', 0),
                "depth_avg_m": props.get('Depth_avg', 0),
                "source": "HydroLAKES",
                "geometry": geometry  # Keep EE geometry for precise analysis
            }
        
        logger.info(f"  ❌ Not found in HydroLAKES: {name}")
        return None
        
    except Exception as e:
        logger.warning(f"  ⚠️ HydroLAKES search failed: {e}")
        return None


def search_known_water_bodies(name: str) -> Optional[Dict]:
    """
    Search known water bodies cache.
    """
    name_lower = name.lower().strip()
    
    # Direct match
    if name_lower in KNOWN_WATER_BODIES:
        data = KNOWN_WATER_BODIES[name_lower]
        logger.info(f"  ✅ Found in known cache: {name}")
        return {
            "name": name.title(),
            "bounds": data["bounds"],
            "country": data["country"],
            "type": data["type"],
            "description": data.get("description", ""),
            "source": "known_cache"
        }
    
    # Partial match
    for key, data in KNOWN_WATER_BODIES.items():
        if name_lower in key or key in name_lower:
            logger.info(f"  ✅ Found in known cache (partial): {key}")
            return {
                "name": key.title(),
                "bounds": data["bounds"],
                "country": data["country"],
                "type": data["type"],
                "description": data.get("description", ""),
                "source": "known_cache"
            }
    
    logger.info(f"  ❌ Not found in known cache: {name}")
    return None


def geocode_location(name: str) -> Optional[Tuple[float, float]]:
    """
    Geocode a location name using OpenStreetMap Nominatim API.
    Returns (longitude, latitude) tuple.
    """
    try:
        logger.info(f"  🌍 Geocoding: {name}")
        
        # Use Nominatim API (free, no key required)
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": name,
            "format": "json",
            "limit": 1,
            "featuretype": "water"  # Prioritize water features
        }
        headers = {
            "User-Agent": "GeoWise-AI/1.0"  # Required by Nominatim
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            results = response.json()
            
            if results:
                result = results[0]
                lon = float(result['lon'])
                lat = float(result['lat'])
                
                logger.info(f"  ✅ Geocoded: {name} → [{lon:.4f}, {lat:.4f}]")
                return (lon, lat)
        
        # Fallback: try without water feature type
        params.pop("featuretype", None)
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            results = response.json()
            if results:
                result = results[0]
                lon = float(result['lon'])
                lat = float(result['lat'])
                logger.info(f"  ✅ Geocoded (fallback): {name} → [{lon:.4f}, {lat:.4f}]")
                return (lon, lat)
        
        logger.warning(f"  ❌ Geocoding failed: {name}")
        return None
        
    except Exception as e:
        logger.warning(f"  ⚠️ Geocoding error: {e}")
        return None


def detect_water_boundary_from_point(lon: float, lat: float, name: str) -> Optional[Dict]:
    """
    Given a point, use JRC max_extent to detect water body boundary.
    Creates a bounding box around the water body.
    """
    try:
        logger.info(f"  🔍 Detecting water boundary from point [{lon:.4f}, {lat:.4f}]")
        
        gsw = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
        max_extent = gsw.select('max_extent')
        
        # Start with a search area (50km buffer)
        center = ee.Geometry.Point([lon, lat])
        search_area = center.buffer(50000)  # 50km
        
        # Check if there's water at this point
        water_at_point = max_extent.reduceRegion(
            reducer=ee.Reducer.max(),
            geometry=center.buffer(1000),  # 1km check
            scale=30
        ).get('max_extent').getInfo()
        
        if not water_at_point:
            # Expand search area
            search_area = center.buffer(100000)  # 100km
            logger.info("  📍 No water at point, expanding search...")
        
        # Get water extent in search area
        water_in_area = max_extent.clip(search_area)
        
        # Find bounds of water
        water_mask = water_in_area.gt(0)
        
        # Reduce to get bounds
        bounds_dict = water_mask.reduceRegion(
            reducer=ee.Reducer.max(),
            geometry=search_area,
            scale=100,
            maxPixels=1e10
        ).getInfo()
        
        if bounds_dict.get('max_extent'):
            # Use the search area bounds but could be refined
            # For now, use a reasonable buffer around the point
            buffer_deg = 0.5  # ~50km at equator
            
            bounds = [
                lon - buffer_deg,
                lat - buffer_deg,
                lon + buffer_deg,
                lat + buffer_deg
            ]
            
            logger.info(f"  ✅ Water boundary detected around point")
            
            return {
                "name": name.title(),
                "country": "Unknown",
                "type": "water body",
                "bounds": bounds,
                "source": "geocoded+jrc",
                "center": [lon, lat]
            }
        
        logger.warning(f"  ❌ No water found near point")
        return None
        
    except Exception as e:
        logger.warning(f"  ⚠️ Water boundary detection failed: {e}")
        return None


def find_water_body(name: str) -> Optional[Dict]:
    """
    Main function to find a water body using the hierarchical strategy:
    1. Search HydroLAKES (1.4M lakes with polygons)
    2. Search known water bodies cache
    3. Geocode + JRC max_extent boundary detection
    
    Returns water body metadata with bounds/geometry.
    """
    logger.info(f"🔍 Finding water body: {name}")
    
    # Strategy 1: Search HydroLAKES
    result = search_hydrolakes(name)
    if result:
        return result
    
    # Strategy 2: Search known cache
    result = search_known_water_bodies(name)
    if result:
        return result
    
    # Strategy 3: Geocode + JRC detection
    coords = geocode_location(name)
    if coords:
        result = detect_water_boundary_from_point(coords[0], coords[1], name)
        if result:
            return result
    
    # Not found anywhere
    logger.warning(f"❌ Water body not found: {name}")
    return None


# ============================================================================
# MAIN TOOL
# ============================================================================

@tool
def analyze_surface_water(
    location_name: str,
    start_year: int = 1984,
    end_year: int = 2021,
    include_animation: bool = True,
    animation_fps: float = 1.0
) -> Dict[str, Any]:
    """
    Analyze surface water changes for ANY water body worldwide.
    
    Uses hierarchical search:
    1. HydroLAKES dataset (1.4M lakes with polygon boundaries)
    2. Known water bodies cache (famous lakes)
    3. Geocoding + JRC max_extent boundary detection
    
    Args:
        location_name: Water body name (e.g., "Aral Sea", "Lake Victoria", "Mono Lake")
        start_year: Analysis start year (1984-2021)
        end_year: Analysis end year (1984-2021)
        include_animation: Generate animation frames and GIF
        animation_fps: Frames per second for GIF (lower = slower)
    
    Returns:
        Dict with tiles, statistics, animation, and time series data
    """
    
    try:
        logger.info(f"💧 Surface water analysis: {location_name} ({start_year}-{end_year})")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 1: FIND WATER BODY (Hierarchical Search)
        # ═══════════════════════════════════════════════════════════════════
        
        water_body = find_water_body(location_name)
        
        if not water_body:
            return {
                "success": False,
                "error": f"Water body not found: {location_name}",
                "suggestion": "Try a more specific name like 'Lake Victoria' or 'Aral Sea'",
                "search_tips": [
                    "Use full name (e.g., 'Lake Titicaca' not just 'Titicaca')",
                    "For reservoirs, try the dam name (e.g., 'Three Gorges')",
                    "For seas, use full name (e.g., 'Caspian Sea')"
                ],
                "available_known_water_bodies": list(KNOWN_WATER_BODIES.keys())
            }
        
        bounds = water_body["bounds"]
        source = water_body.get("source", "unknown")
        
        # Create geometry
        if "geometry" in water_body and water_body["geometry"] is not None:
            # Use precise HydroLAKES geometry
            aoi = water_body["geometry"].bounds()
            use_precise_geometry = True
            logger.info("  📐 Using precise HydroLAKES geometry")
        else:
            # Use bounding box
            aoi = ee.Geometry.Rectangle(bounds)
            use_precise_geometry = False
            logger.info("  📐 Using bounding box geometry")
        
        # Calculate center
        center_lon = (bounds[0] + bounds[2]) / 2
        center_lat = (bounds[1] + bounds[3]) / 2
        
        logger.info(f"  📍 Source: {source}")
        logger.info(f"  📍 Bounds: {bounds}")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 2: LOAD JRC GLOBAL SURFACE WATER DATA
        # ═══════════════════════════════════════════════════════════════════
        
        gsw = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
        gsw_yearly = ee.ImageCollection('JRC/GSW1_4/YearlyHistory')
        
        # Validate years
        valid_start = max(1984, min(start_year, 2021))
        valid_end = max(1984, min(end_year, 2021))
        
        if valid_start != start_year or valid_end != end_year:
            logger.info(f"  ⚠️ Adjusted years: {start_year}-{end_year} → {valid_start}-{valid_end}")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 3: EXTRACT WATER LAYERS
        # ═══════════════════════════════════════════════════════════════════
        
        occurrence = gsw.select('occurrence').clip(aoi)
        max_extent = gsw.select('max_extent').clip(aoi)
        transition = gsw.select('transition').clip(aoi)
        seasonality = gsw.select('seasonality').clip(aoi)
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 4: CALCULATE STATISTICS
        # ═══════════════════════════════════════════════════════════════════
        
        logger.info("  📊 Calculating statistics...")
        
        pixel_area_km2 = 30 * 30 / 1e6
        
        # Maximum historical extent
        max_extent_pixels = max_extent.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi,
            scale=30,
            maxPixels=1e13
        ).get('max_extent')
        max_extent_km2 = ee.Number(max_extent_pixels).multiply(pixel_area_km2).getInfo() or 0
        
        # Current permanent water (>90% occurrence)
        permanent_water = occurrence.gte(90)
        permanent_pixels = permanent_water.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi,
            scale=30,
            maxPixels=1e13
        ).get('occurrence')
        permanent_km2 = ee.Number(permanent_pixels).multiply(pixel_area_km2).getInfo() or 0
        
        # Current seasonal water (10-90% occurrence)
        seasonal_water = occurrence.gte(10).And(occurrence.lt(90))
        seasonal_pixels = seasonal_water.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi,
            scale=30,
            maxPixels=1e13
        ).get('occurrence')
        seasonal_km2 = ee.Number(seasonal_pixels).multiply(pixel_area_km2).getInfo() or 0
        
        # Lost water (transition classes 3 and 6)
        lost_water = transition.eq(3).Or(transition.eq(6))
        lost_pixels = lost_water.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi,
            scale=30,
            maxPixels=1e13
        ).get('transition')
        lost_km2 = ee.Number(lost_pixels).multiply(pixel_area_km2).getInfo() or 0
        
        # New water (transition classes 2 and 5)
        new_water = transition.eq(2).Or(transition.eq(5))
        new_pixels = new_water.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi,
            scale=30,
            maxPixels=1e13
        ).get('transition')
        new_km2 = ee.Number(new_pixels).multiply(pixel_area_km2).getInfo() or 0
        
        # Net change
        net_change_km2 = new_km2 - lost_km2
        
        # Change percentage
        if max_extent_km2 > 0:
            loss_percent = (lost_km2 / max_extent_km2) * 100
            current_percent = ((permanent_km2 + seasonal_km2) / max_extent_km2) * 100
        else:
            loss_percent = 0
            current_percent = 0
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 5: CALCULATE TIME SERIES
        # ═══════════════════════════════════════════════════════════════════

        logger.info("  📈 Calculating time series...")

        time_series_raw = []

        for year in range(valid_start, valid_end + 1, 2):
            try:
                year_img = gsw_yearly.filter(ee.Filter.eq('year', year)).first()
                water = year_img.select('waterClass').gte(2)

                water_pixels = water.reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=aoi,
                    scale=30,
                    maxPixels=1e13
                ).get('waterClass')

                water_km2 = ee.Number(water_pixels).multiply(pixel_area_km2).getInfo() or 0

                time_series_raw.append({
                    "year": year,
                    "water_area_km2": round(water_km2, 2)
                })
            except:
                continue

        # Filter out zero/invalid values (zeros indicate missing data, not dry lakes)
        time_series = [point for point in time_series_raw if point['water_area_km2'] > 0]

        # Check if we have enough valid data points
        if len(time_series) < 2:
            return {
                "success": False,
                "error": "Insufficient valid data points for analysis",
                "details": f"Only {len(time_series)} valid data points found (need at least 2)",
                "data_gaps": len(time_series_raw) - len(time_series)
            }

        # Calculate additional statistics from valid data
        first_valid = time_series[0]
        last_valid = time_series[-1]

        area_start = first_valid['water_area_km2']
        area_end = last_valid['water_area_km2']
        absolute_change = area_end - area_start
        year_span = last_valid['year'] - first_valid['year']

        # Calculate percentages and rates
        change_percent = (absolute_change / area_start * 100) if area_start > 0 else 0
        annual_change_rate = (absolute_change / year_span) if year_span > 0 else 0

        logger.info(f"  📊 Max: {max_extent_km2:.0f} km², Current: {permanent_km2 + seasonal_km2:.0f} km²")
        logger.info(f"  📊 Lost: {lost_km2:.0f} km² ({loss_percent:.1f}%)")
        logger.info(f"  📊 Valid data: {len(time_series)}/{len(time_series_raw)} points ({first_valid['year']}-{last_valid['year']})")
        logger.info(f"  📊 Change: {absolute_change:+.1f} km² ({change_percent:+.1f}%) | {annual_change_rate:+.1f} km²/year")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 6: CREATE BASEMAP
        # ═══════════════════════════════════════════════════════════════════
        
        logger.info("  🗺️ Creating basemap...")
        
        try:
            landsat = ee.ImageCollection('LANDSAT/LC08/C02/T1_TOA') \
                .filterBounds(aoi) \
                .filterDate('2020-01-01', '2022-12-31') \
                .filter(ee.Filter.lt('CLOUD_COVER', 20)) \
                .median() \
                .clip(aoi)
            
            basemap = landsat.visualize(
                bands=['B4', 'B3', 'B2'],
                min=0.05,
                max=0.35,
                gamma=1.3
            )
            basemap_mapid = basemap.getMapId()
            basemap_url = basemap_mapid['tile_fetcher'].url_format
        except Exception as e:
            logger.warning(f"  ⚠️ Basemap failed: {e}")
            basemap = None
            basemap_url = None
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 7: GENERATE TILES
        # ═══════════════════════════════════════════════════════════════════
        
        logger.info("  🎨 Generating tiles...")
        
        # Water occurrence
        occurrence_vis = occurrence.updateMask(occurrence.gt(0)).visualize(
            min=0, max=100,
            palette=PALETTES['water_occurrence'][::-1]
        )
        occurrence_mapid = occurrence_vis.getMapId()
        
        # Current water
        current_water_vis = occurrence.gte(50).selfMask().visualize(
            palette=PALETTES['water_blue']
        )
        current_mapid = current_water_vis.getMapId()
        
        # Maximum extent
        max_extent_vis = max_extent.selfMask().visualize(
            palette=PALETTES['max_extent']
        )
        max_extent_mapid = max_extent_vis.getMapId()
        
        # Lost water
        lost_water_vis = lost_water.selfMask().visualize(
            palette=PALETTES['lost_water']
        )
        lost_mapid = lost_water_vis.getMapId()
        
        # New water
        new_water_vis = new_water.selfMask().visualize(
            palette=PALETTES['new_water']
        )
        new_mapid = new_water_vis.getMapId()
        
        tiles = {
            "basemap": {
                "url": basemap_url,
                "name": "Satellite Basemap",
                "description": "Landsat 8 true color"
            } if basemap_url else None,
            "water_occurrence": {
                "url": occurrence_mapid['tile_fetcher'].url_format,
                "name": "Water Occurrence",
                "description": "% of time water present (1984-2021)"
            },
            "current_water": {
                "url": current_mapid['tile_fetcher'].url_format,
                "name": "Current Water",
                "description": "Water present >50% of time"
            },
            "max_extent": {
                "url": max_extent_mapid['tile_fetcher'].url_format,
                "name": "Maximum Historical Extent",
                "description": "Largest extent ever recorded"
            },
            "lost_water": {
                "url": lost_mapid['tile_fetcher'].url_format,
                "name": "Lost Water",
                "description": "Was water, now dry"
            },
            "new_water": {
                "url": new_mapid['tile_fetcher'].url_format,
                "name": "New Water",
                "description": "Was dry, now water"
            }
        }

        tiles = {k: v for k, v in tiles.items() if v is not None}

        # ═══════════════════════════════════════════════════════════════════
        # STEP 8: GENERATE ANIMATION
        # ═══════════════════════════════════════════════════════════════════
        
        animation_data = None
        
        if include_animation:
            logger.info("  🎬 Generating animation...")
            
            try:
                # Use terrain as fallback basemap for animation
                if basemap is None:
                    terrain = ee.Image('USGS/SRTMGL1_003').clip(aoi)
                    basemap = ee.Terrain.hillshade(terrain).visualize(
                        min=0, max=255,
                        palette=['1a1a1a', '3d3d3d', '666666', '8c8c8c', 'b3b3b3']
                    )
                
                frame_years = [y for y in range(valid_start, valid_end + 1) if y % 2 == 0]
                animation_frames = []
                
                for year in frame_years:
                    try:
                        year_img = gsw_yearly.filter(ee.Filter.eq('year', year)).first()
                        water = year_img.select('waterClass').gte(2).selfMask()
                        water_vis = water.visualize(palette=['00a8ff'])
                        
                        frame = ee.ImageCollection([basemap, water_vis]).mosaic()
                        frame_mapid = frame.getMapId()
                        
                        animation_frames.append({
                            "year": year,
                            "tile_url": frame_mapid['tile_fetcher'].url_format
                        })
                    except:
                        continue
                
                # Generate GIF
                gif_collection = ee.ImageCollection([
                    ee.ImageCollection([
                        basemap,
                        gsw_yearly.filter(ee.Filter.eq('year', y)).first()
                            .select('waterClass').gte(2).selfMask()
                            .visualize(palette=['00a8ff'])
                    ]).mosaic()
                    for y in frame_years
                ])
                
                gif_url = gif_collection.getVideoThumbURL({
                    'region': aoi,
                    'dimensions': 800,
                    'framesPerSecond': animation_fps,
                    'crs': 'EPSG:4326'
                })
                
                animation_data = {
                    "frames": animation_frames,
                    "gif_url": gif_url,
                    "frame_count": len(animation_frames),
                    "years": frame_years,
                    "fps": animation_fps
                }
                
            except Exception as e:
                logger.warning(f"  ⚠️ Animation failed: {e}")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 9: DETERMINE ZOOM LEVEL
        # ═══════════════════════════════════════════════════════════════════
        
        lon_range = bounds[2] - bounds[0]
        lat_range = bounds[3] - bounds[1]
        max_range = max(lon_range, lat_range)
        
        if max_range > 10:
            zoom = 6
        elif max_range > 5:
            zoom = 7
        elif max_range > 2:
            zoom = 8
        elif max_range > 1:
            zoom = 9
        else:
            zoom = 10
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 10: BUILD RESPONSE
        # ═══════════════════════════════════════════════════════════════════
        
        result = {
            "success": True,
            "location": {
                "name": water_body.get("name", location_name.title()),
                "country": water_body.get("country", "Unknown"),
                "type": water_body.get("type", "water body"),
                "description": water_body.get("description", ""),
                "bounds": bounds,
                "center": [center_lon, center_lat],
                "source": source,
                "hydrolakes_area_km2": water_body.get("area_km2")
            },
            "analysis_period": {
                "start_year": valid_start,
                "end_year": valid_end,
                "data_source": "JRC Global Surface Water v1.4"
            },
            "statistics": {
                "max_extent_km2": round(max_extent_km2, 2),
                "current_permanent_km2": round(permanent_km2, 2),
                "current_seasonal_km2": round(seasonal_km2, 2),
                "current_total_km2": round(permanent_km2 + seasonal_km2, 2),
                "lost_water_km2": round(lost_km2, 2),
                "new_water_km2": round(new_km2, 2),
                "net_change_km2": round(net_change_km2, 2),
                "loss_percent": round(loss_percent, 1),
                "current_vs_max_percent": round(current_percent, 1),
                # Additional statistics from valid time series data
                "area_start_km2": round(area_start, 2),
                "area_end_km2": round(area_end, 2),
                "absolute_change_km2": round(absolute_change, 2),
                "change_percent": round(change_percent, 1),
                "annual_change_rate": round(annual_change_rate, 2),
                "valid_data_points": len(time_series),
                "data_gaps": len(time_series_raw) - len(time_series)
            },
            "time_series": time_series,
            "tiles": tiles,
            "map_config": {
                "center": [center_lon, center_lat],
                "zoom": zoom,
                "bounds": bounds
            },
            "animation": animation_data,
            "methodology": {
                "data_source": "JRC Global Surface Water v1.4",
                "lake_detection": source,
                "resolution": "30m (Landsat)",
                "temporal_coverage": "1984-2021"
            },
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Surface water analysis complete: {water_body.get('name', location_name)}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Surface water analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


@tool
def get_available_water_bodies() -> Dict[str, Any]:
    """
    Get list of known water bodies available for quick analysis.
    Note: Any water body can be analyzed via HydroLAKES or geocoding.
    """
    
    categorized = {
        "shrinking_lakes": [],
        "reservoirs": [],
        "deltas": [],
        "other_lakes": []
    }
    
    for name, data in KNOWN_WATER_BODIES.items():
        entry = {
            "name": name.title(),
            "country": data["country"],
            "description": data.get("description", "")
        }
        
        if data["type"] == "reservoir":
            categorized["reservoirs"].append(entry)
        elif data["type"] == "delta":
            categorized["deltas"].append(entry)
        elif any(kw in data.get("description", "").lower() for kw in ["shrunk", "dried", "endangered", "shrinking"]):
            categorized["shrinking_lakes"].append(entry)
        else:
            categorized["other_lakes"].append(entry)
    
    return {
        "success": True,
        "water_bodies": categorized,
        "total_known": len(KNOWN_WATER_BODIES),
        "note": "Any lake worldwide can be analyzed via HydroLAKES (1.4M lakes) or geocoding"
    } 