"""
GEOWISE Spatial Operations
H3 indexing, coordinate conversion, spatial queries, fire-forest correlation
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


def fires_to_h3(fires: List[Dict], resolution: int = 7) -> Dict[str, Dict]:
    """
    Aggregate fire points into H3 hexagons
    
    Args:
        fires: List of fire dicts with latitude/longitude
        resolution: H3 resolution (5-10)
    
    Returns:
        Dict mapping H3 index to aggregated fire data
    """
    h3_data = {}
    
    for fire in fires:
        lat = fire.get('latitude')
        lon = fire.get('longitude')
        
        if lat is None or lon is None:
            continue
        
        h3_index = spatial_ops.lat_lon_to_h3(lat, lon, resolution)
        
        if h3_index not in h3_data:
            h3_data[h3_index] = {
                'fire_count': 0,
                'total_frp': 0,
                'fires': []
            }
        
        h3_data[h3_index]['fire_count'] += 1
        h3_data[h3_index]['total_frp'] += fire.get('frp', 0)
        h3_data[h3_index]['fires'].append(fire)
    
    for h3_index in h3_data:
        count = h3_data[h3_index]['fire_count']
        h3_data[h3_index]['avg_frp'] = h3_data[h3_index]['total_frp'] / count if count > 0 else 0
    
    logger.info(f"Aggregated {len(fires)} fires into {len(h3_data)} H3 hexagons")
    
    return h3_data


def classify_fires_by_h3(
    fire_hexagons: Dict[str, Dict],
    forest_hexagons: Dict[str, float]
) -> Tuple[Dict, Dict, Dict]:
    """
    Classify fires based on forest loss in same hexagon
    
    Args:
        fire_hexagons: H3 index -> fire data
        forest_hexagons: H3 index -> forest loss (ha)
    
    Returns:
        Tuple of (deforestation_hexagons, other_hexagons, stats)
    """
    deforestation_hexagons = {}
    other_hexagons = {}
    
    total_fires = 0
    deforestation_fire_count = 0
    other_fire_count = 0
    
    for h3_index, fire_data in fire_hexagons.items():
        fire_count = fire_data['fire_count']
        total_fires += fire_count
        
        if h3_index in forest_hexagons and forest_hexagons[h3_index] > 0:
            deforestation_hexagons[h3_index] = {
                **fire_data,
                'forest_loss_ha': forest_hexagons[h3_index]
            }
            deforestation_fire_count += fire_count
        else:
            other_hexagons[h3_index] = fire_data
            other_fire_count += fire_count
    
    deforestation_pct = (deforestation_fire_count / total_fires * 100) if total_fires > 0 else 0
    other_pct = (other_fire_count / total_fires * 100) if total_fires > 0 else 0
    
    total_forest_loss = sum(forest_hexagons.values())
    fires_per_ha = deforestation_fire_count / total_forest_loss if total_forest_loss > 0 else 0
    
    stats = {
        'total_fires': total_fires,
        'deforestation_fires': {
            'count': deforestation_fire_count,
            'percentage': round(deforestation_pct, 1),
            'hexagon_count': len(deforestation_hexagons)
        },
        'other_fires': {
            'count': other_fire_count,
            'percentage': round(other_pct, 1),
            'hexagon_count': len(other_hexagons)
        },
        'forest_loss': {
            'total_ha': round(total_forest_loss, 2),
            'hexagon_count': len(forest_hexagons),
            'fires_per_ha': round(fires_per_ha, 2)
        }
    }
    
    logger.info(f"Classification: {deforestation_fire_count} deforestation fires, {other_fire_count} other fires")
    
    return deforestation_hexagons, other_hexagons, stats


def h3_hexagons_to_geojson(hexagons: Dict[str, Dict], hex_type: str) -> Dict:
    """
    Convert H3 hexagons to GeoJSON
    
    Args:
        hexagons: H3 index -> data dict
        hex_type: 'deforestation' or 'other'
    
    Returns:
        GeoJSON FeatureCollection
    """
    features = []
    
    for h3_index, data in hexagons.items():
        boundary = spatial_ops.h3_to_boundary(h3_index)
        coords = [[lon, lat] for lat, lon in boundary]
        coords.append(coords[0])
        
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [coords]
            },
            'properties': {
                'h3_index': h3_index,
                'fire_type': hex_type,
                'fire_count': data.get('fire_count', 0),
                'avg_frp': round(data.get('avg_frp', 0), 2)
            }
        }
        
        if 'forest_loss_ha' in data:
            feature['properties']['forest_loss_ha'] = round(data['forest_loss_ha'], 2)
        
        features.append(feature)
    
    return {
        'type': 'FeatureCollection',
        'features': features
    }


def calculate_correlation_strength(fires_per_ha: float, deforestation_pct: float) -> Dict:
    """
    Determine correlation strength and interpretation
    
    Args:
        fires_per_ha: Fires per hectare in deforested areas
        deforestation_pct: Percentage of fires in deforested areas
    
    Returns:
        Dict with strength and interpretation
    """
    if deforestation_pct > 30 and fires_per_ha > 1.0:
        strength = "STRONG"
        message = f"{deforestation_pct:.1f}% of fires occurred in deforested areas ({fires_per_ha:.2f} fires/ha). Fire is a primary tool for forest clearing."
    elif deforestation_pct > 15 or fires_per_ha > 0.5:
        strength = "MODERATE"
        message = f"{deforestation_pct:.1f}% of fires occurred in deforested areas ({fires_per_ha:.2f} fires/ha). Fire plays a significant role in land clearing."
    else:
        strength = "WEAK"
        message = f"Only {deforestation_pct:.1f}% of fires occurred in deforested areas ({fires_per_ha:.2f} fires/ha). Most fires are from non-forest activities."
    
    return {
        'strength': strength,
        'message': message
    }