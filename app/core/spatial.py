"""
GEOWISE Spatial Operations
H3 indexing, coordinate conversion, spatial queries
"""

from typing import List, Tuple, Optional, Dict, Set
import h3
from shapely.geometry import Point, Polygon, box
from shapely.ops import transform
import pyproj
from functools import lru_cache

from app.schemas.common import BoundingBox
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SpatialOps:
    """Spatial operations using H3 hexagonal indexing."""
    
    @staticmethod
    def lat_lon_to_h3(lat: float, lon: float, resolution: int) -> str:
        """Convert lat/lon to H3 index."""
        if hasattr(h3, 'latlng_to_cell'):
            return h3.latlng_to_cell(lat, lon, resolution)
        return h3.geo_to_h3(lat, lon, resolution)
    
    @staticmethod
    def h3_to_lat_lon(h3_index: str) -> Tuple[float, float]:
        """Convert H3 index to lat/lon centroid."""
        if hasattr(h3, 'cell_to_latlng'):
            return h3.cell_to_latlng(h3_index)
        return h3.h3_to_geo(h3_index)
    
    @staticmethod
    def h3_to_boundary(h3_index: str) -> List[Tuple[float, float]]:
        """Get H3 cell boundary as list of (lat, lon) tuples."""
        if hasattr(h3, 'cell_to_boundary'):
            return list(h3.cell_to_boundary(h3_index))
        return list(h3.h3_to_geo_boundary(h3_index))
    
    @staticmethod
    def get_h3_neighbors(h3_index: str, k: int = 1) -> Set[str]:
        """Get k-ring neighbors of H3 cell."""
        if hasattr(h3, 'grid_disk'):
            return h3.grid_disk(h3_index, k)
        return h3.k_ring(h3_index, k)
    
    @staticmethod
    def h3_parent(h3_index: str, parent_resolution: int) -> str:
        """Get parent H3 cell at lower resolution."""
        if hasattr(h3, 'cell_to_parent'):
            return h3.cell_to_parent(h3_index, parent_resolution)
        return h3.h3_to_parent(h3_index, parent_resolution)
    
    @staticmethod
    def h3_children(h3_index: str, child_resolution: int) -> Set[str]:
        """Get children H3 cells at higher resolution."""
        if hasattr(h3, 'cell_to_children'):
            return h3.cell_to_children(h3_index, child_resolution)
        return h3.h3_to_children(h3_index, child_resolution)
    
    @staticmethod
    def bbox_to_h3_cells(bbox: BoundingBox, resolution: int) -> Set[str]:
        """Get all H3 cells covering a bounding box."""
        polygon = box(bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat)
        coords = list(polygon.exterior.coords)
        
        geojson_polygon = {
            "type": "Polygon",
            "coordinates": [[list(coord) for coord in coords]]
        }
        
        if hasattr(h3, 'polygon_to_cells'):
            return h3.polygon_to_cells(geojson_polygon, resolution)
        return h3.polyfill(geojson_polygon, resolution)
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in km using Haversine formula."""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371.0
        lat1_rad, lon1_rad = radians(lat1), radians(lon1)
        lat2_rad, lon2_rad = radians(lat2), radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    @staticmethod
    @lru_cache(maxsize=1024)
    def get_h3_area_km2(resolution: int) -> float:
        """Get average H3 cell area in km² for a resolution."""
        areas = {
            0: 4357449.416078383, 1: 609788.441794133, 2: 86801.780398997,
            3: 12392.264862127, 4: 1770.323552528, 5: 252.903858182,
            6: 36.129062164, 7: 5.161293360, 8: 0.737327598,
            9: 0.105332513, 10: 0.015047502, 11: 0.002149643,
            12: 0.000307092, 13: 0.000043870, 14: 0.000006267,
            15: 0.000000895
        }
        return areas.get(resolution, 0.0)


spatial_ops = SpatialOps()