"""
TiTiler Service - Convert MPC STAC items to map tiles
FIXED: Proper URL generation for Microsoft Planetary Computer
"""

from typing import Dict, Any, Optional, List
import math
import logging

logger = logging.getLogger(__name__)


class TiTilerService:
    """TiTiler service for generating tile URLs from STAC items"""
    
    def __init__(self):
        self.titiler_endpoint = "https://planetarycomputer.microsoft.com/api/data/v1"
        
        # Asset configurations per collection
        self.collection_assets = {
            "sentinel-2-l2a": {
                "natural_color": ["B04", "B03", "B02"],  # Red, Green, Blue
                "false_color": ["B08", "B04", "B03"],    # NIR, Red, Green
                "ndvi_bands": ["B08", "B04"]              # NIR, Red for NDVI
            },
            "landsat-c2-l2": {
                "natural_color": ["red", "green", "blue"],
                "false_color": ["nir08", "red", "green"],
                "ndvi_bands": ["nir08", "red"]
            },
            "hls": {
                "natural_color": ["B04", "B03", "B02"],
                "false_color": ["B05", "B04", "B03"],
                "ndvi_bands": ["B05", "B04"]
            }
        }
    
    def get_tile_url(
        self,
        collection: str,
        item_id: str,
        assets: List[str],
        rescale: Optional[str] = None,
        colormap: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate TiTiler tile URL for a STAC item.
        
        Args:
            collection: Collection ID (e.g., "sentinel-2-l2a")
            item_id: STAC item ID
            assets: List of asset names (e.g., ["B04", "B03", "B02"])
            rescale: Rescale range (e.g., "0,3000")
            colormap: Colormap name for single-band visualization
        
        Returns:
            Tile URL template with {z}/{x}/{y} placeholders
        """
        
        try:
            # ✅ CORRECTED: Proper MPC TiTiler endpoint format
            tile_url = f"{self.titiler_endpoint}/item/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png"
            
            # Build parameters
            params = []
            params.append(f"collection={collection}")
            params.append(f"item={item_id}")
            
            for asset in assets:
                params.append(f"assets={asset}")
            
            if rescale:
                params.append(f"rescale={rescale}")
            
            if colormap:
                params.append(f"colormap_name={colormap}")
            
            # Performance optimization: bilinear resampling for smoother tiles
            params.append("resampling=bilinear")
            
            # ✅ CORRECTED: Combine with proper query string
            full_url = f"{tile_url}?{'&'.join(params)}"
            
            logger.info(f"✅ Generated tile URL for {item_id[:30]}...")
            return full_url
            
        except Exception as e:
            logger.error(f"Failed to generate tile URL: {e}")
            return None
    
    def get_rgb_tile_url(
        self,
        collection: str,
        item_id: str,
        layer_type: str = "natural_color"
    ) -> Optional[str]:
        """
        Get RGB composite tile URL.
        
        Args:
            collection: Collection ID
            item_id: STAC item ID
            layer_type: "natural_color" or "false_color"
        
        Returns:
            Tile URL template
        """
        
        collection_config = self.collection_assets.get(collection)
        
        if not collection_config:
            logger.warning(f"Unknown collection: {collection}")
            return None
        
        assets = collection_config.get(layer_type, collection_config.get("natural_color"))
        
        # Default rescale values per collection
        rescale = None
        if collection == "sentinel-2-l2a":
            rescale = "0,3000"
        elif collection == "landsat-c2-l2":
            # Landsat C2 L2 uses scaled integers (multiply by 0.0000275, add -0.2)
            # Typical visible range: 7000-30000 for good contrast
            rescale = "7000,30000"
        elif collection == "hls":
            # HLS uses scaled integers similar to Sentinel-2
            rescale = "0,3000"
        
        return self.get_tile_url(
            collection=collection,
            item_id=item_id,
            assets=assets,
            rescale=rescale
        )
    
    def get_ndvi_tile_url(
        self,
        collection: str,
        item_id: str
    ) -> Optional[str]:
        """
        Get NDVI tile URL.
        
        Args:
            collection: Collection ID
            item_id: STAC item ID
        
        Returns:
            Tile URL with greens colormap
        """
        
        collection_config = self.collection_assets.get(collection)
        
        if not collection_config:
            return None
        
        ndvi_bands = collection_config.get("ndvi_bands")
        
        if not ndvi_bands:
            return None
        
        return self.get_tile_url(
            collection=collection,
            item_id=item_id,
            assets=ndvi_bands,
            colormap="greens",
            rescale="-1,1"
        )
    
    @staticmethod
    def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple:
        """
        Convert lat/lon to tile coordinates.
        
        Args:
            lat: Latitude
            lon: Longitude
            zoom: Zoom level
        
        Returns:
            (x, y) tile coordinates
        """
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y
    
    @staticmethod
    def bbox_to_center(bbox: List[float]) -> tuple:
        """
        Get center point from bbox.
        
        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat]
        
        Returns:
            (center_lat, center_lon)
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        center_lon = (min_lon + max_lon) / 2
        center_lat = (min_lat + max_lat) / 2
        return center_lat, center_lon


# Singleton instance
titiler_service = TiTilerService()