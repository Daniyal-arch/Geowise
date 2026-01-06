"""
Air Quality Analysis Tool - Sentinel-5P
app/llm/tools/air_quality_tool.py

Analyzes air quality using Sentinel-5P satellite data.
Supports: NO2, SO2, CO, O3, CH4, HCHO, Aerosol Index
"""

from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
import ee
import requests
from datetime import datetime

from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# POLLUTANT CONFIGURATIONS
# ============================================================================

POLLUTANTS = {
    'NO2': {
        'collection': 'COPERNICUS/S5P/OFFL/L3_NO2',
        'band': 'tropospheric_NO2_column_number_density',
        'scale': 1e6,  # Convert mol/m² to µmol/m²
        'unit': 'µmol/m²',
        'name': 'Nitrogen Dioxide',
        'sources': 'Traffic, power plants, industry',
        'health_impact': 'Respiratory issues, smog formation',
        'vis_params': {'min': 0, 'max': 150},
        'palette': ['00ff00', 'ffff00', 'ff8c00', 'ff4500', 'ff0000', '8b0000', '4b0082'],
        'who_guideline': 40,  # µg/m³ annual mean (approximate conversion)
    },
    'SO2': {
        'collection': 'COPERNICUS/S5P/OFFL/L3_SO2',
        'band': 'SO2_column_number_density',
        'scale': 1e6,
        'unit': 'µmol/m²',
        'name': 'Sulfur Dioxide',
        'sources': 'Coal plants, refineries, volcanoes',
        'health_impact': 'Breathing problems, acid rain',
        'vis_params': {'min': 0, 'max': 500},
        'palette': ['00bfff', '00ffff', '7fff00', 'ffff00', 'ff8c00', 'ff0000', '8b0000'],
        'who_guideline': 20,
    },
    'CO': {
        'collection': 'COPERNICUS/S5P/OFFL/L3_CO',
        'band': 'CO_column_number_density',
        'scale': 1e3,  # Convert to mmol/m²
        'unit': 'mmol/m²',
        'name': 'Carbon Monoxide',
        'sources': 'Fires, vehicles, industry',
        'health_impact': 'Reduces blood oxygen levels',
        'vis_params': {'min': 20, 'max': 50},
        'palette': ['006400', '228b22', '7cfc00', 'ffff00', 'daa520', '8b4513', '3d2314'],
        'who_guideline': None,
    },
    'O3': {
        'collection': 'COPERNICUS/S5P/OFFL/L3_O3',
        'band': 'O3_column_number_density',
        'scale': 1e3,
        'unit': 'mmol/m²',
        'name': 'Ozone',
        'sources': 'Photochemical reactions (smog)',
        'health_impact': 'Respiratory issues, crop damage',
        'vis_params': {'min': 100, 'max': 150},
        'palette': ['0000ff', '00ffff', '00ff00', 'ffff00', 'ff8c00', 'ff0000'],
        'who_guideline': 100,
    },
    'CH4': {
        'collection': 'COPERNICUS/S5P/OFFL/L3_CH4',
        'band': 'CH4_column_volume_mixing_ratio_dry_air',
        'scale': 1,  # Already in ppb
        'unit': 'ppb',
        'name': 'Methane',
        'sources': 'Landfills, agriculture, oil/gas leaks',
        'health_impact': 'Greenhouse gas, climate change',
        'vis_params': {'min': 1750, 'max': 1950},
        'palette': ['00ff00', '7fff00', 'ffff00', 'ff8c00', 'ff4500', 'ff0000'],
        'who_guideline': None,
    },
    'HCHO': {
        'collection': 'COPERNICUS/S5P/OFFL/L3_HCHO',
        'band': 'tropospheric_HCHO_column_number_density',
        'scale': 1e6,
        'unit': 'µmol/m²',
        'name': 'Formaldehyde',
        'sources': 'Fires, vegetation, industry',
        'health_impact': 'Eye/respiratory irritation, carcinogenic',
        'vis_params': {'min': 0, 'max': 100},
        'palette': ['e6f5ff', 'b3e0ff', '66c2ff', '1aa3ff', '0080ff', '0059b3'],
        'who_guideline': None,
    },
    'AEROSOL': {
        'collection': 'COPERNICUS/S5P/OFFL/L3_AER_AI',
        'band': 'absorbing_aerosol_index',
        'scale': 1,
        'unit': 'index',
        'name': 'Aerosol Index',
        'sources': 'Dust storms, smoke, pollution particles',
        'health_impact': 'Respiratory and cardiovascular issues',
        'vis_params': {'min': -1, 'max': 3},
        'palette': ['f0f8ff', 'e6e6fa', 'd3d3d3', 'a9a9a9', '808080', '8b4513', 'd2691e'],
        'who_guideline': None,
    }
}

# Primary pollutants for default analysis
PRIMARY_POLLUTANTS = ['NO2', 'SO2', 'CO', 'AEROSOL']

# All available pollutants
ALL_POLLUTANTS = list(POLLUTANTS.keys())


# ============================================================================
# KNOWN LOCATIONS (Cities with high pollution interest)
# ============================================================================

KNOWN_LOCATIONS = {
    # South Asia (High pollution)
    "lahore": {"center": [74.3587, 31.5204], "buffer_km": 60, "country": "Pakistan"},
    "karachi": {"center": [67.0011, 24.8607], "buffer_km": 70, "country": "Pakistan"},
    "delhi": {"center": [77.1025, 28.7041], "buffer_km": 70, "country": "India"},
    "mumbai": {"center": [72.8777, 19.0760], "buffer_km": 60, "country": "India"},
    "dhaka": {"center": [90.4125, 23.8103], "buffer_km": 50, "country": "Bangladesh"},
    
    # East Asia
    "beijing": {"center": [116.4074, 39.9042], "buffer_km": 80, "country": "China"},
    "shanghai": {"center": [121.4737, 31.2304], "buffer_km": 70, "country": "China"},
    "tokyo": {"center": [139.6917, 35.6895], "buffer_km": 60, "country": "Japan"},
    "seoul": {"center": [126.9780, 37.5665], "buffer_km": 50, "country": "South Korea"},
    
    # Middle East
    "dubai": {"center": [55.2708, 25.2048], "buffer_km": 50, "country": "UAE"},
    "riyadh": {"center": [46.6753, 24.7136], "buffer_km": 60, "country": "Saudi Arabia"},
    "cairo": {"center": [31.2357, 30.0444], "buffer_km": 50, "country": "Egypt"},
    "tehran": {"center": [51.3890, 35.6892], "buffer_km": 60, "country": "Iran"},
    
    # Europe
    "london": {"center": [-0.1276, 51.5074], "buffer_km": 50, "country": "UK"},
    "paris": {"center": [2.3522, 48.8566], "buffer_km": 50, "country": "France"},
    "moscow": {"center": [37.6173, 55.7558], "buffer_km": 70, "country": "Russia"},
    
    # Americas
    "los angeles": {"center": [-118.2437, 34.0522], "buffer_km": 70, "country": "USA"},
    "new york": {"center": [-74.0060, 40.7128], "buffer_km": 60, "country": "USA"},
    "mexico city": {"center": [-99.1332, 19.4326], "buffer_km": 60, "country": "Mexico"},
    "sao paulo": {"center": [-46.6333, -23.5505], "buffer_km": 70, "country": "Brazil"},
    
    # Africa
    "lagos": {"center": [3.3792, 6.5244], "buffer_km": 50, "country": "Nigeria"},
    "johannesburg": {"center": [28.0473, -26.2041], "buffer_km": 50, "country": "South Africa"},
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_location_geometry(location_name: str, buffer_km: Optional[float] = None) -> Optional[Dict]:
    """Get location center and buffer geometry."""
    
    location_key = location_name.lower().strip()
    
    # Direct match
    if location_key in KNOWN_LOCATIONS:
        loc_data = KNOWN_LOCATIONS[location_key]
        buffer = buffer_km or loc_data["buffer_km"]
        return {
            "name": location_name.title(),
            "center": loc_data["center"],
            "buffer_km": buffer,
            "country": loc_data["country"],
            "source": "known_locations"
        }
    
    # Partial match
    for key, data in KNOWN_LOCATIONS.items():
        if location_key in key or key in location_key:
            buffer = buffer_km or data["buffer_km"]
            return {
                "name": key.title(),
                "center": data["center"],
                "buffer_km": buffer,
                "country": data["country"],
                "source": "known_locations"
            }
    
    # Geocoding fallback
    return geocode_location(location_name, buffer_km)


def geocode_location(name: str, buffer_km: Optional[float] = None) -> Optional[Dict]:
    """Geocode a location using Nominatim API."""
    
    try:
        logger.info(f"  🌍 Geocoding: {name}")
        
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": name,
            "format": "json",
            "limit": 1
        }
        headers = {"User-Agent": "GeoWise-AI/1.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            results = response.json()
            if results:
                result = results[0]
                lon = float(result['lon'])
                lat = float(result['lat'])
                
                logger.info(f"  ✅ Geocoded: {name} → [{lon:.4f}, {lat:.4f}]")
                
                return {
                    "name": name.title(),
                    "center": [lon, lat],
                    "buffer_km": buffer_km or 50,  # Default 50km
                    "country": "Unknown",
                    "source": "geocoded"
                }
        
        logger.warning(f"  ❌ Geocoding failed: {name}")
        return None
        
    except Exception as e:
        logger.warning(f"  ⚠️ Geocoding error: {e}")
        return None


def get_air_quality_level(no2_value: float) -> Dict[str, Any]:
    """Determine air quality level based on NO2 value."""
    
    # AQI-style categories for NO2 (µmol/m²)
    if no2_value < 30:
        return {"level": "Good", "color": "#00e400", "emoji": "🟢", "health_advice": "Air quality is satisfactory"}
    elif no2_value < 60:
        return {"level": "Moderate", "color": "#ffff00", "emoji": "🟡", "health_advice": "Acceptable for most people"}
    elif no2_value < 90:
        return {"level": "Unhealthy for Sensitive", "color": "#ff7e00", "emoji": "🟠", "health_advice": "Sensitive groups should limit outdoor exposure"}
    elif no2_value < 120:
        return {"level": "Unhealthy", "color": "#ff0000", "emoji": "🔴", "health_advice": "Everyone should reduce prolonged outdoor exposure"}
    elif no2_value < 150:
        return {"level": "Very Unhealthy", "color": "#8f3f97", "emoji": "🟣", "health_advice": "Health alert - everyone should avoid outdoor activity"}
    else:
        return {"level": "Hazardous", "color": "#7e0023", "emoji": "⚫", "health_advice": "Health emergency - stay indoors"}


# ============================================================================
# MAIN TOOL
# ============================================================================

@tool
def analyze_air_quality(
    location_name: str,
    year: int = 2023,
    pollutants: Optional[List[str]] = None,
    buffer_km: Optional[float] = None,
    include_monthly_trend: bool = True,
    include_yearly_trend: bool = True,
    trend_start_year: int = 2019
) -> Dict[str, Any]:
    """
    Analyze air quality for a location using Sentinel-5P satellite data.
    
    Args:
        location_name: City or location name (e.g., "Lahore", "Beijing", "Los Angeles")
        year: Analysis year (2018-2024, Sentinel-5P data starts from late 2018)
        pollutants: List of pollutants to analyze. Options: NO2, SO2, CO, O3, CH4, HCHO, AEROSOL
                   Default: ['NO2', 'SO2', 'CO', 'AEROSOL']
        buffer_km: Radius around location in km (default varies by city)
        include_monthly_trend: Include monthly trend data for the analysis year
        include_yearly_trend: Include yearly trend data
        trend_start_year: Start year for yearly trend (default 2019)
    
    Returns:
        Dict with tiles, statistics, monthly/yearly trends
    """
    
    try:
        logger.info(f"💨 Air quality analysis: {location_name} ({year})")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 1: GET LOCATION
        # ═══════════════════════════════════════════════════════════════════
        
        location = get_location_geometry(location_name, buffer_km)
        
        if not location:
            return {
                "success": False,
                "error": f"Location not found: {location_name}",
                "suggestion": "Try a major city name like 'Lahore', 'Delhi', 'Beijing'",
                "available_cities": list(KNOWN_LOCATIONS.keys())
            }
        
        center = location["center"]
        buffer = location["buffer_km"]
        
        # Create EE geometry
        center_point = ee.Geometry.Point(center)
        aoi = center_point.buffer(buffer * 1000)
        
        logger.info(f"  📍 Location: {location['name']}, {location['country']}")
        logger.info(f"  📍 Center: {center}, Buffer: {buffer}km")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 2: VALIDATE PARAMETERS
        # ═══════════════════════════════════════════════════════════════════
        
        # Validate year (Sentinel-5P starts late 2018)
        valid_year = max(2019, min(year, 2024))
        if valid_year != year:
            logger.info(f"  ⚠️ Adjusted year: {year} → {valid_year}")
        
        # Validate pollutants
        if pollutants is None:
            pollutants = PRIMARY_POLLUTANTS
        else:
            pollutants = [p.upper() for p in pollutants if p.upper() in POLLUTANTS]
            if not pollutants:
                pollutants = PRIMARY_POLLUTANTS
        
        logger.info(f"  🔬 Pollutants: {pollutants}")
        
        # Date range for analysis year
        start_date = f"{valid_year}-01-01"
        end_date = f"{valid_year}-12-31"
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 3: CALCULATE ANNUAL STATISTICS FOR EACH POLLUTANT
        # ═══════════════════════════════════════════════════════════════════
        
        logger.info("  📊 Calculating annual statistics...")
        
        pollutant_stats = {}
        tiles = {}
        
        for pollutant_key in pollutants:
            config = POLLUTANTS[pollutant_key]
            
            try:
                # Get annual mean
                collection = ee.ImageCollection(config['collection']) \
                    .select(config['band']) \
                    .filterDate(start_date, end_date) \
                    .filterBounds(aoi)
                
                annual_mean = collection.mean().multiply(config['scale']).clip(aoi)
                
                # Calculate statistics
                stats = annual_mean.reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.minMax(),
                        sharedInputs=True
                    ),
                    geometry=aoi,
                    scale=1000,
                    maxPixels=1e13
                ).getInfo()
                
                # Extract values
                band_name = config['band']
                mean_val = stats.get(f'{band_name}_mean') or stats.get(band_name) or 0
                max_val = stats.get(f'{band_name}_max', 0)
                min_val = stats.get(f'{band_name}_min', 0)
                
                pollutant_stats[pollutant_key] = {
                    "name": config['name'],
                    "mean": round(mean_val, 2) if mean_val else 0,
                    "max": round(max_val, 2) if max_val else 0,
                    "min": round(min_val, 2) if min_val else 0,
                    "unit": config['unit'],
                    "sources": config['sources'],
                    "health_impact": config['health_impact']
                }
                
                # Generate tile URL
                vis_params = {
                    'min': config['vis_params']['min'],
                    'max': config['vis_params']['max'],
                    'palette': config['palette']
                }
                
                map_id = annual_mean.visualize(**vis_params).getMapId()
                
                tiles[pollutant_key] = {
                    "url": map_id['tile_fetcher'].url_format,
                    "name": f"{config['name']} ({pollutant_key})",
                    "description": f"Annual mean {valid_year} - {config['sources']}",
                    "unit": config['unit'],
                    "vis_params": vis_params
                }
                
                logger.info(f"  ✅ {pollutant_key}: mean={mean_val:.2f} {config['unit']}")
                
            except Exception as e:
                logger.warning(f"  ⚠️ {pollutant_key} failed: {e}")
                pollutant_stats[pollutant_key] = {
                    "name": config['name'],
                    "error": str(e)
                }
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 4: CALCULATE AIR QUALITY LEVEL (based on NO2)
        # ═══════════════════════════════════════════════════════════════════
        
        air_quality_level = None
        if 'NO2' in pollutant_stats and 'mean' in pollutant_stats['NO2']:
            no2_mean = pollutant_stats['NO2']['mean']
            air_quality_level = get_air_quality_level(no2_mean)
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 5: CALCULATE MONTHLY TREND (for analysis year)
        # ═══════════════════════════════════════════════════════════════════
        
        monthly_trend = None
        
        if include_monthly_trend and 'NO2' in pollutants:
            logger.info("  📈 Calculating monthly trend...")
            
            monthly_data = []
            config = POLLUTANTS['NO2']
            
            for month in range(1, 13):
                try:
                    month_start = ee.Date.fromYMD(valid_year, month, 1)
                    month_end = month_start.advance(1, 'month')
                    
                    monthly_mean = ee.ImageCollection(config['collection']) \
                        .select(config['band']) \
                        .filterDate(month_start, month_end) \
                        .filterBounds(aoi) \
                        .mean() \
                        .multiply(config['scale'])
                    
                    mean_val = monthly_mean.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=aoi,
                        scale=1000,
                        maxPixels=1e13
                    ).get(config['band']).getInfo()
                    
                    monthly_data.append({
                        "month": month,
                        "month_name": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month - 1],
                        "value": round(mean_val, 2) if mean_val else 0
                    })
                except Exception as e:
                    logger.warning(f"  ⚠️ Month {month} failed: {e}")
                    monthly_data.append({"month": month, "value": None})
            
            monthly_trend = {
                "pollutant": "NO2",
                "unit": config['unit'],
                "year": valid_year,
                "data": monthly_data
            }
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 6: CALCULATE YEARLY TREND
        # ═══════════════════════════════════════════════════════════════════
        
        yearly_trend = None
        
        if include_yearly_trend and 'NO2' in pollutants:
            logger.info("  📈 Calculating yearly trend...")
            
            yearly_data = []
            config = POLLUTANTS['NO2']
            
            for trend_year in range(trend_start_year, valid_year + 1):
                try:
                    year_start = f"{trend_year}-01-01"
                    year_end = f"{trend_year}-12-31"
                    
                    yearly_mean = ee.ImageCollection(config['collection']) \
                        .select(config['band']) \
                        .filterDate(year_start, year_end) \
                        .filterBounds(aoi) \
                        .mean() \
                        .multiply(config['scale'])
                    
                    mean_val = yearly_mean.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=aoi,
                        scale=1000,
                        maxPixels=1e13
                    ).get(config['band']).getInfo()
                    
                    yearly_data.append({
                        "year": trend_year,
                        "value": round(mean_val, 2) if mean_val else 0
                    })
                except Exception as e:
                    logger.warning(f"  ⚠️ Year {trend_year} failed: {e}")
                    yearly_data.append({"year": trend_year, "value": None})
            
            # Calculate trend (change from first to last year)
            valid_data = [d for d in yearly_data if d.get("value")]
            if len(valid_data) >= 2:
                first_val = valid_data[0]["value"]
                last_val = valid_data[-1]["value"]
                change = last_val - first_val
                change_percent = (change / first_val * 100) if first_val > 0 else 0
            else:
                change = 0
                change_percent = 0
            
            yearly_trend = {
                "pollutant": "NO2",
                "unit": config['unit'],
                "start_year": trend_start_year,
                "end_year": valid_year,
                "data": yearly_data,
                "total_change": round(change, 2),
                "change_percent": round(change_percent, 1)
            }
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 7: DETERMINE ZOOM LEVEL
        # ═══════════════════════════════════════════════════════════════════
        
        if buffer > 80:
            zoom = 8
        elif buffer > 50:
            zoom = 9
        elif buffer > 30:
            zoom = 10
        else:
            zoom = 11
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 8: BUILD RESPONSE
        # ═══════════════════════════════════════════════════════════════════
        
        result = {
            "success": True,
            "location": {
                "name": location["name"],
                "country": location["country"],
                "center": center,
                "buffer_km": buffer,
                "source": location.get("source", "unknown")
            },
            "analysis_period": {
                "year": valid_year,
                "start_date": start_date,
                "end_date": end_date
            },
            "air_quality_level": air_quality_level,
            "pollutant_statistics": pollutant_stats,
            "monthly_trend": monthly_trend,
            "yearly_trend": yearly_trend,
            "tiles": tiles,
            "map_config": {
                "center": center,
                "zoom": zoom
            },
            "methodology": {
                "data_source": "Copernicus Sentinel-5P",
                "resolution": "~7km (resampled to 1km grid)",
                "temporal_coverage": "2018-present",
                "pollutants_analyzed": pollutants
            },
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Air quality analysis complete for {location['name']}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Air quality analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


@tool
def get_available_pollutants() -> Dict[str, Any]:
    """
    Get list of available pollutants from Sentinel-5P.
    
    Returns:
        Dict with pollutant details and availability
    """
    
    pollutant_list = []
    
    for key, config in POLLUTANTS.items():
        pollutant_list.append({
            "code": key,
            "name": config['name'],
            "unit": config['unit'],
            "sources": config['sources'],
            "health_impact": config['health_impact']
        })
    
    return {
        "success": True,
        "pollutants": pollutant_list,
        "primary_pollutants": PRIMARY_POLLUTANTS,
        "data_source": "Copernicus Sentinel-5P",
        "temporal_coverage": "2018-present",
        "note": "CO2 is NOT available in Sentinel-5P. Use OCO-2/OCO-3 for CO2."
    }


@tool
def compare_air_quality_years(
    location_name: str,
    year1: int,
    year2: int,
    pollutant: str = "NO2"
) -> Dict[str, Any]:
    """
    Compare air quality between two years (e.g., before/after COVID).
    
    Args:
        location_name: City or location name
        year1: First year (e.g., 2019)
        year2: Second year (e.g., 2020)
        pollutant: Pollutant to compare (default NO2)
    
    Returns:
        Dict with comparison statistics and change tiles
    """
    
    try:
        logger.info(f"💨 Air quality comparison: {location_name} ({year1} vs {year2})")
        
        # Get location
        location = get_location_geometry(location_name)
        
        if not location:
            return {
                "success": False,
                "error": f"Location not found: {location_name}"
            }
        
        center = location["center"]
        buffer = location["buffer_km"]
        
        center_point = ee.Geometry.Point(center)
        aoi = center_point.buffer(buffer * 1000)
        
        # Validate pollutant
        pollutant = pollutant.upper()
        if pollutant not in POLLUTANTS:
            pollutant = "NO2"
        
        config = POLLUTANTS[pollutant]
        
        # Get annual means for both years
        def get_annual_mean(year):
            return ee.ImageCollection(config['collection']) \
                .select(config['band']) \
                .filterDate(f"{year}-01-01", f"{year}-12-31") \
                .filterBounds(aoi) \
                .mean() \
                .multiply(config['scale']) \
                .clip(aoi)
        
        mean1 = get_annual_mean(year1)
        mean2 = get_annual_mean(year2)
        
        # Calculate statistics
        stats1 = mean1.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=1000,
            maxPixels=1e13
        ).get(config['band']).getInfo()
        
        stats2 = mean2.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=1000,
            maxPixels=1e13
        ).get(config['band']).getInfo()
        
        # Calculate change
        change = stats2 - stats1
        change_percent = (change / stats1 * 100) if stats1 > 0 else 0
        
        # Create difference layer
        diff_image = mean2.subtract(mean1)
        
        # Generate tiles
        vis_params = {
            'min': config['vis_params']['min'],
            'max': config['vis_params']['max'],
            'palette': config['palette']
        }
        
        diff_vis = {
            'min': -50,
            'max': 50,
            'palette': ['0000ff', '00ffff', 'ffffff', 'ffff00', 'ff0000']
        }
        
        tile1 = mean1.visualize(**vis_params).getMapId()
        tile2 = mean2.visualize(**vis_params).getMapId()
        tile_diff = diff_image.visualize(**diff_vis).getMapId()
        
        return {
            "success": True,
            "location": {
                "name": location["name"],
                "country": location["country"],
                "center": center
            },
            "comparison": {
                "pollutant": pollutant,
                "pollutant_name": config['name'],
                "unit": config['unit'],
                "year1": year1,
                "year2": year2,
                "mean_year1": round(stats1, 2),
                "mean_year2": round(stats2, 2),
                "absolute_change": round(change, 2),
                "percent_change": round(change_percent, 1),
                "trend": "increased" if change > 0 else "decreased" if change < 0 else "stable"
            },
            "tiles": {
                f"{pollutant}_{year1}": {
                    "url": tile1['tile_fetcher'].url_format,
                    "name": f"{config['name']} ({year1})"
                },
                f"{pollutant}_{year2}": {
                    "url": tile2['tile_fetcher'].url_format,
                    "name": f"{config['name']} ({year2})"
                },
                "change": {
                    "url": tile_diff['tile_fetcher'].url_format,
                    "name": f"Change ({year2} - {year1})",
                    "description": "Blue = decreased, Red = increased"
                }
            },
            "map_config": {
                "center": center,
                "zoom": 9
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Comparison failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }