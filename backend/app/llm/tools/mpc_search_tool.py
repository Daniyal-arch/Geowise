"""
MPC Image Search Tool - With Robust Geocoding and TiTiler Integration
"""

from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from pystac_client import Client
import planetary_computer as pc


# ============================================================================
# GEOCODING - Try multiple approaches
# ============================================================================

def geocode_to_bbox_sync(
    location_name: str,
    buffer_km: float = 10.0,
    country_hint: Optional[str] = None
) -> Optional[List[float]]:
    """
    Synchronous geocoding with fallback to hardcoded locations
    """
    
    # Method 1: Try httpx (async library)
    try:
        import httpx
        import asyncio
        
        async def _geocode():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    params = {
                        "q": location_name,
                        "format": "json",
                        "limit": 1
                    }
                    
                    if country_hint:
                        params["countrycodes"] = country_hint.lower()
                    
                    response = await client.get(
                        "https://nominatim.openstreetmap.org/search",
                        params=params,
                        headers={"User-Agent": "GeoWise-AI/1.0"}
                    )
                    
                    if response.status_code == 200:
                        results = response.json()
                        if results:
                            bb = results[0].get("boundingbox")
                            if bb:
                                return [
                                    float(bb[2]), float(bb[0]),
                                    float(bb[3]), float(bb[1])
                                ]
            except Exception as e:
                print(f"  ⚠️  httpx error: {e}")
            return None
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        bbox = loop.run_until_complete(_geocode())
        loop.close()
        
        if bbox:
            return ensure_minimum_bbox(bbox, buffer_km)
    
    except ImportError:
        print("  ⚠️  httpx not installed")
    except Exception as e:
        print(f"  ⚠️  Async geocoding failed: {e}")
    
    # Method 2: Try requests (sync library)
    try:
        import requests
        
        params = {
            "q": location_name,
            "format": "json",
            "limit": 1
        }
        
        if country_hint:
            params["countrycodes"] = country_hint.lower()
        
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers={"User-Agent": "GeoWise-AI/1.0"},
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()
            if results:
                bb = results[0].get("boundingbox")
                if bb:
                    bbox = [
                        float(bb[2]), float(bb[0]),
                        float(bb[3]), float(bb[1])
                    ]
                    return ensure_minimum_bbox(bbox, buffer_km)
    
    except ImportError:
        print("  ⚠️  requests not installed")
    except Exception as e:
        print(f"  ⚠️  Sync geocoding failed: {e}")
    
    # Method 3: Fallback to hardcoded locations
    print(f"  ℹ️  Using hardcoded location database...")
    return get_hardcoded_bbox(location_name, buffer_km)


def get_hardcoded_bbox(location_name: str, buffer_km: float) -> Optional[List[float]]:
    """Fallback hardcoded locations for Pakistan and major cities"""
    
    LOCATIONS = {
        # Country codes and names (default to Karachi area for Pakistan)
        "pakistan": [60.8786, 23.6345, 77.8374, 37.0841],  # Full Pakistan
        "pak": [66.2862312, 24.4273517, 67.5827753, 25.676796],  # Default to Karachi
        "pk": [66.2862312, 24.4273517, 67.5827753, 25.676796],
        
        # Pakistan Cities
        "lahore": [74.1541829, 31.4056822, 74.4741829, 31.7256822],
        "karachi": [66.2862312, 24.4273517, 67.5827753, 25.676796],
        "islamabad": [72.9051511, 33.5338118, 73.2251511, 33.8538118],
        "rawalpindi": [73.0169, 33.5651, 73.1169, 33.6651],
        "faisalabad": [73.0169, 31.3700, 73.1369, 31.4900],
        "multan": [71.4200, 30.1575, 71.5400, 30.2775],
        "peshawar": [71.5000, 33.9900, 71.6200, 34.1100],
        "quetta": [66.9500, 30.1700, 67.0700, 30.2900],
        
        # Pakistan Provinces
        "punjab": [69.261757, 27.7055479, 75.3814778, 34.018757],
        "sindh": [66.883333, 25.633333, 68.283333, 27.033333],
        "sindh province": [66.883333, 25.633333, 68.283333, 27.033333],
        "khyber pakhtunkhwa": [69.3451, 31.6160, 74.7900, 37.0960],
        "kpk": [69.3451, 31.6160, 74.7900, 37.0960],
        "balochistan": [61.6160, 24.8618, 69.8800, 31.4990],
        
        # Pakistan Districts
        "dadu": [67.5, 26.1, 68.5, 27.1],
        "dadu district": [66.883333, 25.633333, 68.283333, 27.033333],
        "hyderabad": [68.3, 25.3, 68.5, 25.5],
        "sukkur": [68.8, 27.6, 69.0, 27.8],
        "larkana": [68.1, 27.4, 68.3, 27.6],
        
        # International (for testing)
        "new york": [-74.258843, 40.476578, -73.700233, 40.91763],
        "london": [-0.5103, 51.2867, 0.3340, 51.6919],
        "tokyo": [139.5688, 35.5232, 139.9192, 35.8169],
    }
    
    key = location_name.lower().strip()
    bbox = LOCATIONS.get(key)
    
    if bbox:
        print(f"  ✅ Found in database: {location_name}")
        return bbox
    
    # Try partial match
    for loc_key, loc_bbox in LOCATIONS.items():
        if key in loc_key or loc_key in key:
            print(f"  ✅ Partial match: {loc_key}")
            return loc_bbox
    
    print(f"  ❌ Location '{location_name}' not found")
    return None


def ensure_minimum_bbox(bbox: List[float], buffer_km: float) -> List[float]:
    """Ensure bbox has minimum size"""
    
    min_lon, min_lat, max_lon, max_lat = bbox
    
    width = max_lon - min_lon
    height = max_lat - min_lat
    
    buffer_degrees = buffer_km / 111.0
    min_size = buffer_degrees * 2
    
    if width < min_size:
        center_lon = (min_lon + max_lon) / 2
        min_lon = center_lon - buffer_degrees
        max_lon = center_lon + buffer_degrees
    
    if height < min_size:
        center_lat = (min_lat + max_lat) / 2
        min_lat = center_lat - buffer_degrees
        max_lat = center_lat + buffer_degrees
    
    return [min_lon, min_lat, max_lon, max_lat]


# ============================================================================
# TILE URL GENERATION
# ============================================================================

def add_tile_urls_to_images(collection: str, images: List[Dict]) -> List[Dict]:
    """
    Add TiTiler tile URLs to image results.
    
    Args:
        collection: Collection ID (e.g., "sentinel-2-l2a")
        images: List of image dicts from MPC search
    
    Returns:
        Images with tile_urls added
    """
    
    try:
        from app.services.titiler_service import titiler_service
        
        for img in images:
            item_id = img.get("id")
            
            if not item_id:
                continue
            
            # Generate tile URLs for different visualizations
            img["tile_urls"] = {
                "natural_color": titiler_service.get_rgb_tile_url(
                    collection, item_id, "natural_color"
                ),
                "false_color": titiler_service.get_rgb_tile_url(
                    collection, item_id, "false_color"
                ),
                "ndvi": titiler_service.get_ndvi_tile_url(
                    collection, item_id
                )
            }
            
            print(f"  ✅ Generated tile URLs for {item_id[:30]}...")
        
        return images
        
    except Exception as e:
        print(f"  ⚠️  Could not generate tile URLs: {e}")
        # Return images without tile URLs
        return images


# ============================================================================
# MPC SEARCH TOOL
# ============================================================================

COLLECTION_ALIASES = {
    "sentinel-2": "sentinel-2-l2a",
    "sentinel2": "sentinel-2-l2a",
    "s2": "sentinel-2-l2a",
    "landsat": "landsat-c2-l2",
    "hls": "hls",
}


@tool
def search_mpc_images(
    location_name: str,
    collection: str = "sentinel-2-l2a",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_cloud_cover: int = 30,
    limit: int = 20,
    country_hint: Optional[str] = None,
    smart_coverage: bool = False  #  Set to False for now
) -> Dict[str, Any]:
    """
    Search Microsoft Planetary Computer for satellite imagery.
    
    Args:
        location_name: Place name (e.g., "Lahore", "Sindh Province")
        collection: "sentinel-2", "landsat", or "hls"
        start_date: YYYY-MM-DD format
        end_date: YYYY-MM-DD format
        max_cloud_cover: 0-100
        limit: Number of results
        country_hint: Country code (e.g., "PK")
        smart_coverage: Enable smart coverage optimization
    
    Returns:
        Search results with images and tile URLs
    """
    
    try:
        print(f"🔍 Searching MPC for {collection} images of {location_name}")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 1: GET BOUNDARY (try OpenStreetMap first, fallback to geocoding)
        # ═══════════════════════════════════════════════════════════════════
        
        boundary_data = None
        
        try:
            import asyncio
            import nest_asyncio
            from app.services.boundary_service import boundary_service
            
            print(f"  🌍 Fetching exact boundary...")
            
            # Use nest_asyncio to allow nested event loops (FastAPI already has one running)
            nest_asyncio.apply()
            
            # Run async boundary fetch
            loop = asyncio.get_event_loop()
            boundary_data = loop.run_until_complete(
                boundary_service.get_city_boundary(location_name, country=country_hint)
            )
            
            if boundary_data:
                bbox = boundary_data["bbox"]
                print(f"  ✅ Got boundary: {boundary_data['area_km2']:.0f} km²")
            else:
                print(f"  ⚠️  No boundary found, using geocoding...")
                bbox = geocode_to_bbox_sync(location_name, buffer_km=20, country_hint=country_hint)
        
        except ImportError as e:
            print(f"  ⚠️  nest_asyncio not installed, using geocoding fallback: {e}")
            bbox = geocode_to_bbox_sync(location_name, buffer_km=20, country_hint=country_hint)
        except Exception as e:
            print(f"  ⚠️  Boundary fetch failed: {e}")
            bbox = geocode_to_bbox_sync(location_name, buffer_km=20, country_hint=country_hint)
        
        if not bbox:
            return {
                "success": False,
                "error": f"Could not geocode location: {location_name}",
                "suggestion": "Try: Lahore, Karachi, Sindh, Dadu, Punjab, Islamabad"
            }
        
        print(f"  ✅ Bbox: [{bbox[0]:.4f}, {bbox[1]:.4f}, {bbox[2]:.4f}, {bbox[3]:.4f}]")
        
        # Calculate area
        from shapely.geometry import box
        area_km2 = box(*bbox).area * 111 * 111
        print(f"  📏 Area: {area_km2:,.0f} km²")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 2: SEARCH MPC
        # ═══════════════════════════════════════════════════════════════════
        
        collection_id = COLLECTION_ALIASES.get(collection.lower(), collection)
        
        catalog = Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=pc.sign_inplace
        )
        
        search_params = {
            "collections": [collection_id],
            "bbox": bbox,
            "limit": limit
        }
        
        if start_date and end_date:
            search_params["datetime"] = f"{start_date}/{end_date}"
        
        if collection_id in ["sentinel-2-l2a", "landsat-c2-l2", "hls"]:
            search_params["query"] = {"eo:cloud_cover": {"lt": max_cloud_cover}}
        
        print(f"  🛰️  Searching {collection_id}...")
        print(f"  📅 Date range: {start_date} to {end_date}")
        print(f"  ☁️  Max cloud: {max_cloud_cover}%")
        
        search = catalog.search(**search_params)
        items = list(search.items())
        
        print(f"  ✅ Found {len(items)} images")
        
        if not items:
            return {
                "success": False,
                "error": f"No images found for {location_name} in the specified time period",
                "suggestion": "Try expanding the date range or increasing max_cloud_cover"
            }
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 3: EXTRACT IMAGE METADATA
        # ═══════════════════════════════════════════════════════════════════
        
        images = []
        for item in items:
            images.append({
                "id": item.id,
                "datetime": item.datetime.isoformat() if item.datetime else None,
                "cloud_cover": item.properties.get("eo:cloud_cover"),
                "collection": item.collection_id,
                "bbox": item.bbox if hasattr(item, 'bbox') else bbox
            })
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 4: ADD TILE URLs
        # ═══════════════════════════════════════════════════════════════════
        
        print(f"  🎨 Generating tile URLs...")
        images = add_tile_urls_to_images(collection_id, images)
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 5: BUILD RESPONSE
        # ═══════════════════════════════════════════════════════════════════
        
        result = {
            "success": True,
            "location": location_name,
            "bbox": bbox,
            "area_km2": round(area_km2, 2),
            "collection": collection_id,
            "images_found": len(images),
            "images": images,
            "message": f"Found {len(images)} images with tile URLs"
        }
        
        # Add boundary if found
        if boundary_data:
            result["boundary"] = boundary_data["boundary"]
            result["boundary_source"] = "OpenStreetMap"
        
        print(f"✅ MPC search complete: {len(images)} images ready")
        
        return result
        
    except Exception as e:
        print(f"❌ MPC search error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }