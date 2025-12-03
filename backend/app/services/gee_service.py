"""
GEOWISE - Google Earth Engine Service
======================================
Add this file to: app/services/gee_service.py

Provides Hansen Global Forest Change data via Google Earth Engine.
SUPPORTS ALL COUNTRIES DYNAMICALLY using Earth Engine boundaries.
"""

import os
import json
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import ee

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

HANSEN_DATASET = 'UMD/hansen/global_forest_change_2024_v1_12'
CACHE_DURATION = timedelta(hours=23)

# ⭐ OPTIONAL: Keep custom configs for countries needing special handling
CUSTOM_COUNTRY_CONFIGS = {
    'BRA': {'name': 'Brazil', 'center': [-51.93, -14.24], 'zoom': 4},
    'IDN': {'name': 'Indonesia', 'center': [118.02, -2.55], 'zoom': 5},
    'COG': {'name': 'Congo', 'center': [15.83, -0.23], 'zoom': 6},
    'PAK': {'name': 'Pakistan', 'center': [69.34, 30.38], 'zoom': 6},
    'IND': {'name': 'India', 'center': [78.96, 20.59], 'zoom': 5},
}

# ============================================================================
# GEE SERVICE CLASS
# ============================================================================

class GEEService:
    """Google Earth Engine service for Hansen forest data"""
    
    def __init__(self):
        """Initialize GEE Service"""
        self.initialized = False
        self.project_id = None
        self._tile_cache = {}  # Cache for tile URLs (expires after 23 hours)
    
    def initialize(self, key_file: str = 'gee-service-account-key.json', 
                   project_id: str = 'active-apogee-444711-k5') -> bool:
        """Initialize Google Earth Engine"""
        try:
            if self.initialized:
                return True
            
            if not os.path.exists(key_file):
                logger.error(f"Service account key not found: {key_file}")
                return False
            
            with open(key_file, 'r') as f:
                key_data = json.load(f)
            
            credentials = ee.ServiceAccountCredentials(
                email=key_data['client_email'],
                key_file=key_file
            )
            
            ee.Initialize(credentials=credentials, project=project_id)
            ee.Number(1).getInfo()
            
            self.initialized = True
            self.project_id = project_id
            
            logger.info("✅ Google Earth Engine initialized!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize GEE: {e}")
            return False
    
    def get_country_info(self, country_iso: str) -> Dict:
        """
        Get country information dynamically from Earth Engine
        Falls back to custom configs if available
        """
        country_iso = country_iso.upper()
        
        # Check custom configs first
        if country_iso in CUSTOM_COUNTRY_CONFIGS:
            logger.info(f"Using custom config for {country_iso}")
            return CUSTOM_COUNTRY_CONFIGS[country_iso]
        
        try:
            # ⭐ Use Earth Engine's built-in country boundaries
            # Dataset: LSIB (Large Scale International Boundary) or USDOS
            countries = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017')
            
            # Find country by ISO code
            country = countries.filter(ee.Filter.eq('country_co', country_iso)).first()
            
            # Get country name
            country_name = country.get('country_na').getInfo()
            
            # Calculate bounding box and center
            bounds = country.geometry().bounds().getInfo()['coordinates'][0]
            
            # Extract min/max lon/lat
            lons = [coord[0] for coord in bounds]
            lats = [coord[1] for coord in bounds]
            
            min_lon, max_lon = min(lons), max(lons)
            min_lat, max_lat = min(lats), max(lats)
            
            # Calculate center
            center_lon = (min_lon + max_lon) / 2
            center_lat = (min_lat + max_lat) / 2
            
            # Calculate zoom based on size
            width = max_lon - min_lon
            height = max_lat - min_lat
            max_dimension = max(width, height)
            
            if max_dimension > 50:
                zoom = 4
            elif max_dimension > 20:
                zoom = 5
            elif max_dimension > 10:
                zoom = 6
            else:
                zoom = 7
            
            country_info = {
                'name': country_name,
                'center': [center_lon, center_lat],
                'zoom': zoom,
                'bounds': [min_lon, min_lat, max_lon, max_lat]
            }
            
            logger.info(f"✅ Dynamic country info for {country_iso}: {country_name}")
            return country_info
            
        except Exception as e:
            logger.error(f"Failed to get country info for {country_iso}: {e}")
            
            # ⭐ FALLBACK: Return default values
            return {
                'name': country_iso,
                'center': [0, 0],
                'zoom': 5,
                'bounds': None
            }
    
    def get_forest_tiles(self, country_iso: str, include_lossyear: bool = False, 
                        force_refresh: bool = False) -> Dict:
        """Get map tile URLs for Hansen forest data - WORKS FOR ANY COUNTRY"""
        if not self.initialized:
            raise RuntimeError("GEE not initialized")
        
        country_iso = country_iso.upper()
        
        if len(country_iso) != 3:
            raise ValueError(f"Country code must be exactly 3 letters, got: {country_iso}")
        
        # Check cache
        cache_key = f"{country_iso}_{include_lossyear}"
        if not force_refresh and cache_key in self._tile_cache:
            cached = self._tile_cache[cache_key]
            cache_time = datetime.fromisoformat(cached['generated_at'])
            if datetime.now() - cache_time < CACHE_DURATION:
                logger.info(f"✅ Using cached tiles for {country_iso}")
                return cached
        
        # ⭐ Get country info dynamically
        country_data = self.get_country_info(country_iso)
        
        # Load Hansen dataset
        gfc = ee.Image('UMD/hansen/global_forest_change_2024_v1_12')
        
        # CRITICAL: Use the EXACT visualization from official GEE docs
        # https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2024_v1_12
        
        # BASELINE - Tree Cover 2000
        treeCover = gfc.select(['treecover2000'])
        treeCoverVis = {
            'min': 0,
            'max': 100,
            'palette': ['black', 'green']
        }
        baseline_mapid = treeCover.visualize(**treeCoverVis).getMapId()
        
        # LOSS - Forest Loss (with lossyear coloring)
        treeLoss = gfc.select(['lossyear'])
        treeLossVis = {
            'min': 0,
            'max': 24,
            'palette': ['yellow', 'red']
        }
        loss_mapid = treeLoss.visualize(**treeLossVis).getMapId()
        
        # GAIN - Forest Gain (with masking!)
        treeGain = gfc.select(['gain'])
        treeGainMasked = treeGain.updateMask(treeGain)  # ⭐ Mask zeros!
        treeGainVis = {
            'palette': ['blue']
        }
        gain_mapid = treeGainMasked.visualize(**treeGainVis).getMapId()
        
        result = {
            'success': True,
            'country_iso': country_iso,
            'country_name': country_data['name'],
            'center': country_data['center'],
            'zoom': country_data['zoom'],
            'layers': {
                'baseline': {
                    'name': 'Tree Cover 2000',
                    'tile_url': baseline_mapid['tile_fetcher'].url_format,
                    'description': 'Forest baseline from year 2000',
                    'year_range': '2000'
                },
                'loss': {
                    'name': 'Forest Loss by Year',
                    'tile_url': loss_mapid['tile_fetcher'].url_format,
                    'description': 'Forest loss 2001-2024 (yellow=recent, red=older)',
                    'year_range': '2001-2024'
                },
                'gain': {
                    'name': 'Forest Gain',
                    'tile_url': gain_mapid['tile_fetcher'].url_format,
                    'description': 'Forest gain 2000-2012',
                    'year_range': '2000-2012'
                }
            },
            'generated_at': datetime.now().isoformat()
        }
        
        # ⭐ Cache the result
        self._tile_cache[cache_key] = result
        
        logger.info(f"✅ Generated tiles for {country_iso} ({country_data['name']})")
        return result

# Global instance
gee_service = GEEService()

def initialize_gee_service(key_file: str = 'gee-service-account-key.json', 
                          project_id: str = 'active-apogee-444711-k5') -> bool:
    """Initialize GEE service (call from main.py startup)"""
    return gee_service.initialize(key_file, project_id)