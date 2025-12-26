"""
Coverage Optimizer - Intelligently select images to cover full area
"""

from typing import List, Dict, Any, Tuple, Optional
from shapely.geometry import box, Polygon, MultiPolygon
from shapely.ops import unary_union
import math
from pystac_client import Client
import planetary_computer as pc
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CoverageOptimizer:
    """
    Optimizes satellite image selection for complete area coverage
    """
    
    def __init__(self):
        self.catalog = Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=pc.sign_inplace
        )
    
    def create_grid(self, bbox: List[float], grid_size: float = 0.5) -> List[Polygon]:
        """
        Create grid cells over bbox
        
        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat]
            grid_size: Cell size in degrees (~50km at equator)
        
        Returns:
            List of grid cell polygons
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        
        cells = []
        
        lon = min_lon
        while lon < max_lon:
            lat = min_lat
            while lat < max_lat:
                cell = box(
                    lon,
                    lat,
                    min(lon + grid_size, max_lon),
                    min(lat + grid_size, max_lat)
                )
                cells.append(cell)
                lat += grid_size
            lon += grid_size
        
        logger.info(f"Created {len(cells)} grid cells for coverage analysis")
        return cells
    
    def calculate_coverage(
        self,
        image_bbox: List[float],
        target_bbox: List[float]
    ) -> float:
        """
        Calculate what % of target bbox is covered by image
        
        Args:
            image_bbox: Image bounds [min_lon, min_lat, max_lon, max_lat]
            target_bbox: Target area bounds
        
        Returns:
            Coverage percentage (0-100)
        """
        image_poly = box(*image_bbox)
        target_poly = box(*target_bbox)
        
        intersection = image_poly.intersection(target_poly)
        coverage = (intersection.area / target_poly.area) * 100
        
        return coverage
    
    def find_optimal_images(
        self,
        location_name: str,
        bbox: List[float],
        collection: str,
        start_date: str,
        end_date: str,
        max_cloud_cover: int = 30,
        target_coverage: float = 90.0
    ) -> Dict[str, Any]:
        """
        Find minimum set of images for complete coverage
        
        Args:
            location_name: Place name
            bbox: Search area [min_lon, min_lat, max_lon, max_lat]
            collection: Collection ID
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            max_cloud_cover: Max cloud percentage
            target_coverage: Desired coverage % (default 90%)
        
        Returns:
            Dict with selected images and coverage stats
        """
        
        logger.info(f"🔍 Finding optimal coverage for {location_name}")
        logger.info(f"   Bbox: {bbox}")
        logger.info(f"   Target coverage: {target_coverage}%")
        
        # Step 1: Search all available images
        search_params = {
            "collections": [collection],
            "bbox": bbox,
            "datetime": f"{start_date}/{end_date}",
            "limit": 100  # Get many candidates
        }
        
        if collection in ["sentinel-2-l2a", "landsat-c2-l2", "hls"]:
            search_params["query"] = {"eo:cloud_cover": {"lt": max_cloud_cover}}
        
        search = self.catalog.search(**search_params)
        items = list(search.items())
        
        logger.info(f"   Found {len(items)} candidate images")
        
        if not items:
            return {
                "success": False,
                "error": "No images found for this area and time period",
                "images": [],
                "coverage_percent": 0
            }
        
        # Step 2: Sort by cloud cover (prefer clearer images)
        candidates = []
        for item in items:
            item_bbox = item.bbox if hasattr(item, 'bbox') else bbox
            cloud_cover = item.properties.get("eo:cloud_cover", 100)
            
            coverage = self.calculate_coverage(item_bbox, bbox)
            
            candidates.append({
                "id": item.id,
                "datetime": item.datetime.isoformat() if item.datetime else None,
                "cloud_cover": cloud_cover,
                "collection": item.collection_id,
                "bbox": item_bbox,
                "coverage_percent": coverage
            })
        
        # Sort: Best coverage first, then lowest clouds
        candidates.sort(key=lambda x: (-x["coverage_percent"], x["cloud_cover"]))
        
        logger.info(f"   Best single image covers: {candidates[0]['coverage_percent']:.1f}%")
        
        # Step 3: Greedy algorithm to select minimum images
        selected = []
        target_poly = box(*bbox)
        covered_area = Polygon()
        total_coverage = 0.0
        
        for candidate in candidates:
            if total_coverage >= target_coverage:
                break
            
            image_poly = box(*candidate["bbox"])
            
            # Calculate new area this image would cover
            new_coverage = image_poly.difference(covered_area)
            new_area_percent = (new_coverage.area / target_poly.area) * 100
            
            # Only add if it increases coverage significantly
            if new_area_percent > 5.0 or len(selected) == 0:
                selected.append(candidate)
                covered_area = unary_union([covered_area, image_poly])
                total_coverage = (covered_area.area / target_poly.area) * 100
                
                logger.info(f"   Selected image {len(selected)}: {candidate['id'][:30]}... "
                           f"(+{new_area_percent:.1f}% coverage, total: {total_coverage:.1f}%)")
        
        # Step 4: Return results
        logger.info(f"✅ Selected {len(selected)} images for {total_coverage:.1f}% coverage")
        
        return {
            "success": True,
            "location": location_name,
            "bbox": bbox,
            "collection": collection,
            "images_found": len(items),
            "images_selected": len(selected),
            "coverage_percent": round(total_coverage, 2),
            "target_coverage": target_coverage,
            "images": selected,
            "message": f"Selected {len(selected)} images covering {total_coverage:.1f}% of {location_name}"
        }
    
    def get_coverage_map(
        self,
        images: List[Dict],
        bbox: List[float]
    ) -> Dict[str, Any]:
        """
        Generate coverage visualization data
        
        Args:
            images: Selected images
            bbox: Target bbox
        
        Returns:
            GeoJSON features for visualization
        """
        
        features = []
        
        # Add target area
        features.append({
            "type": "Feature",
            "properties": {
                "type": "target_area",
                "name": "Search Area"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [bbox[0], bbox[1]],
                    [bbox[2], bbox[1]],
                    [bbox[2], bbox[3]],
                    [bbox[0], bbox[3]],
                    [bbox[0], bbox[1]]
                ]]
            }
        })
        
        # Add image footprints
        for i, img in enumerate(images, 1):
            img_bbox = img["bbox"]
            features.append({
                "type": "Feature",
                "properties": {
                    "type": "image_footprint",
                    "image_id": img["id"],
                    "cloud_cover": img["cloud_cover"],
                    "datetime": img["datetime"],
                    "sequence": i
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [img_bbox[0], img_bbox[1]],
                        [img_bbox[2], img_bbox[1]],
                        [img_bbox[2], img_bbox[3]],
                        [img_bbox[0], img_bbox[3]],
                        [img_bbox[0], img_bbox[1]]
                    ]]
                }
            })
        
        return {
            "type": "FeatureCollection",
            "features": features
        }


# Singleton instance
coverage_optimizer = CoverageOptimizer()