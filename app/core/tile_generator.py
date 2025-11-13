"""
GEOWISE Map Tile Generation
Generate vector tiles for fire density visualization
"""

from typing import List, Dict, Any, Optional, Tuple
import json
from collections import defaultdict

from app.core.spatial import spatial_ops
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TileGenerator:
    """Generate map tiles for visualization."""
    
    @staticmethod
    def aggregate_to_geojson(
        aggregated_data: List[Dict[str, Any]],
        properties: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Convert aggregated H3 data to GeoJSON."""
        
        features = []
        
        for cell in aggregated_data:
            h3_index = cell["h3_index"]
            boundary = spatial_ops.h3_to_boundary(h3_index)
            
            coordinates = [[list(reversed(point)) for point in boundary]]
            coordinates[0].append(coordinates[0][0])
            
            props = {
                "h3_index": h3_index,
                "fire_count": cell["fire_count"]
            }
            
            if properties:
                for prop in properties:
                    if prop in cell:
                        props[prop] = cell[prop]
            else:
                props.update({
                    "total_frp": cell.get("total_frp"),
                    "avg_frp": cell.get("avg_frp"),
                    "max_frp": cell.get("max_frp"),
                    "high_confidence_count": cell.get("high_confidence_count", 0)
                })
            
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": coordinates
                },
                "properties": props
            })
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
    
    @staticmethod
    def generate_heatmap_data(
        aggregated_data: List[Dict[str, Any]],
        value_field: str = "fire_count"
    ) -> List[List[float]]:
        """Generate heatmap data [lat, lon, intensity]."""
        
        heatmap_data = []
        
        for cell in aggregated_data:
            lat = cell.get("centroid_lat")
            lon = cell.get("centroid_lon")
            value = cell.get(value_field, 0)
            
            if lat and lon and value:
                heatmap_data.append([lat, lon, float(value)])
        
        return heatmap_data
    
    @staticmethod
    def generate_cluster_data(
        fires: List[Dict[str, Any]],
        zoom_level: int
    ) -> List[Dict[str, Any]]:
        """Generate clustered fire points for map display."""
        
        h3_resolution = min(9, max(5, zoom_level - 3))
        
        clusters = defaultdict(list)
        
        for fire in fires:
            h3_index = spatial_ops.lat_lon_to_h3(
                fire["latitude"],
                fire["longitude"],
                h3_resolution
            )
            clusters[h3_index].append(fire)
        
        cluster_data = []
        
        for h3_index, fire_group in clusters.items():
            lat, lon = spatial_ops.h3_to_lat_lon(h3_index)
            
            cluster_data.append({
                "lat": lat,
                "lon": lon,
                "count": len(fire_group),
                "h3_index": h3_index,
                "avg_frp": sum(f.get("frp", 0) for f in fire_group) / len(fire_group) if fire_group else 0
            })
        
        return cluster_data


tile_generator = TileGenerator()