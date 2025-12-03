"""Microsoft Planetary Computer Service - Smart Sampling"""

import requests
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
import planetary_computer as pc
import numpy as np
from typing import Dict, List, Optional, Tuple

from app.utils.logger import get_logger

logger = get_logger(__name__)


class MPCService:
    """Microsoft Planetary Computer STAC API client"""
    
    def __init__(self):
        self.stac_url = "https://planetarycomputer.microsoft.com/api/stac/v1"
        self.collection_id = "io-lulc-annual-v02"
    
    def get_strategic_regions(self, country_iso: str) -> List[List[float]]:
        """
        Get strategic forest regions for sampling
        
        Uses known forested areas instead of uniform grid
        """
        
        regions = {
            "BRA": [
                # Amazon regions (known forest areas)
                [-62.0, -3.0, -61.0, -2.0],    # Manaus region
                [-60.0, -3.0, -59.0, -2.0],    # Central Amazon
                [-55.0, -3.5, -54.0, -2.5],    # Eastern Amazon
                [-58.0, -1.0, -57.0, 0.0],     # Northern Amazon
                [-63.0, -5.0, -62.0, -4.0],    # Western Amazon
                # Cerrado/Forest transition
                [-48.0, -15.0, -47.0, -14.0],  # Central Brazil
                # Atlantic Forest
                [-44.0, -23.0, -43.0, -22.0],  # Rio region
            ],
            "IDN": [
                # Sumatra
                [100.0, -2.0, 101.0, -1.0],
                [101.0, 0.0, 102.0, 1.0],
                # Kalimantan (Borneo)
                [110.0, -1.0, 111.0, 0.0],
                [112.0, 0.5, 113.0, 1.5],
                # Papua
                [138.0, -3.0, 139.0, -2.0],
            ],
            "PAK": [
                # Northern forests
                [73.0, 35.0, 74.0, 36.0],
                [74.5, 34.5, 75.5, 35.5],
            ]
        }
        
        return regions.get(country_iso, [])
    
    def search_items(self, bbox: List[float], year: int, limit: int = 10) -> List[Dict]:
        """Search for land cover items"""
        
        search_url = f"{self.stac_url}/search"
        
        search_params = {
            "collections": [self.collection_id],
            "bbox": bbox,
            "datetime": f"{year}-01-01/{year}-12-31",
            "limit": limit
        }
        
        try:
            response = requests.post(search_url, json=search_params, timeout=60)
            
            if response.status_code == 200:
                results = response.json()
                features = results.get('features', [])
                return features
            else:
                logger.error(f"Search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []
    
    def get_forest_pixels_in_bbox(
        self, 
        bbox: List[float], 
        year: int,
        max_pixels: int = 10000
    ) -> Tuple[np.ndarray, List[Tuple[float, float]]]:
        """
        Get forest pixels within a bounding box
        
        Args:
            bbox: [west, south, east, north] in WGS84
            year: Year to query
            max_pixels: Maximum pixels to return (for performance)
        
        Returns:
            Tuple of (forest_mask, pixel_coordinates)
        """
        items = self.search_items(bbox, year, limit=1)
        
        if not items:
            logger.warning(f"No MPC items found for bbox {bbox}")
            return np.array([]), []
        
        item = items[0]
        signed_item = pc.sign(item)
        
        data_url = signed_item['assets']['data']['href']
        
        try:
            with rasterio.open(data_url) as src:
                
                # Transform bbox to source CRS
                west, south, east, north = bbox
                transformed_bounds = transform_bounds(
                    'EPSG:4326',
                    src.crs,
                    west, south, east, north
                )
                
                # Check if bounds overlap with raster
                raster_bounds = src.bounds
                
                # Calculate overlap
                overlap_west = max(transformed_bounds[0], raster_bounds.left)
                overlap_south = max(transformed_bounds[1], raster_bounds.bottom)
                overlap_east = min(transformed_bounds[2], raster_bounds.right)
                overlap_north = min(transformed_bounds[3], raster_bounds.top)
                
                if overlap_west >= overlap_east or overlap_south >= overlap_north:
                    logger.warning(f"Bbox doesn't overlap with raster coverage")
                    return np.array([]), []
                
                # Use overlap bounds
                window = from_bounds(
                    overlap_west, 
                    overlap_south, 
                    overlap_east, 
                    overlap_north, 
                    src.transform
                )
                
                # Check window validity
                if window.width <= 0 or window.height <= 0:
                    logger.warning(f"Invalid window size: {window}")
                    return np.array([]), []
                
                # Limit window size for performance
                if window.width * window.height > max_pixels:
                    scale = np.sqrt(max_pixels / (window.width * window.height))
                    new_width = int(window.width * scale)
                    new_height = int(window.height * scale)
                    
                    window = rasterio.windows.Window(
                        window.col_off,
                        window.row_off,
                        new_width,
                        new_height
                    )
                    logger.info(f"Limited window to {new_width}x{new_height} pixels")
                
                # Read data
                data = src.read(1, window=window)
                
                if data.size == 0:
                    logger.warning(f"Empty data read from window")
                    return np.array([]), []
                
                logger.info(f"Read data shape: {data.shape}")
                logger.info(f"Unique classes: {np.unique(data)}")
                
                # Forest is class 2
                forest_mask = (data == 2)
                forest_pixel_count = forest_mask.sum()
                
                logger.info(f"Found {forest_pixel_count} forest pixels")
                
                if forest_pixel_count == 0:
                    return np.array([]), []
                
                # Sample pixels if too many
                rows, cols = np.where(forest_mask)
                
                if len(rows) > max_pixels:
                    indices = np.random.choice(len(rows), max_pixels, replace=False)
                    rows = rows[indices]
                    cols = cols[indices]
                    logger.info(f"Sampled {max_pixels} pixels from {forest_pixel_count}")
                
                # Get coordinates
                forest_coords = []
                
                for row, col in zip(rows, cols):
                    pixel_x = window.col_off + col
                    pixel_y = window.row_off + row
                    
                    lon, lat = rasterio.transform.xy(
                        src.transform,
                        pixel_y,
                        pixel_x
                    )
                    
                    # Transform back to WGS84
                    from pyproj import Transformer
                    transformer = Transformer.from_crs(
                        src.crs,
                        'EPSG:4326',
                        always_xy=True
                    )
                    lon_wgs84, lat_wgs84 = transformer.transform(lon, lat)
                    
                    forest_coords.append((lat_wgs84, lon_wgs84))
                
                logger.info(f"Extracted {len(forest_coords)} forest coordinates")
                
                return forest_mask, forest_coords
                
        except Exception as e:
            logger.error(f"Error reading raster: {str(e)}")
            return np.array([]), []
    
    def get_country_bbox(self, country_iso: str) -> Optional[List[float]]:
        """Get bounding box for country"""
        
        country_bboxes = {
            "BRA": [-73.9872, -33.7683, -34.7299, 5.2842],
            "IDN": [95.0, -11.0, 141.0, 6.0],
            "PAK": [60.87, 23.63, 77.84, 37.08],
        }
        
        return country_bboxes.get(country_iso)