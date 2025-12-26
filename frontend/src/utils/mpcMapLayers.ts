/**
 * MPC Map Layers Utility
 * Handles adding/removing MPC visualization to MapLibre GL map
 * Supports city boundaries, satellite imagery, and auto-zoom
 * Location: frontend/src/utils/mpcMapLayers.ts
 */

import maplibregl from 'maplibre-gl';
import type { MPCNLPResponse, MPCImage } from '@/types/mpc';
import { getCollectionColor } from '@/types/mpc';

// ============================================================================
// LAYER/SOURCE IDS
// ============================================================================

const MPC_SOURCE_IDS = {
  searchArea: 'mpc-search-area-source',
  imageMarker: 'mpc-image-marker-source',
  imagery: 'mpc-imagery-source',
  boundary: 'mpc-boundary-source',
  clipMask: 'mpc-clip-mask-source',
} as const;

const MPC_LAYER_IDS = {
  searchArea: 'mpc-search-area-layer',
  imageMarker: 'mpc-image-marker-layer',
  naturalColor: 'mpc-natural-color-layer',
  falseColor: 'mpc-false-color-layer',
  ndvi: 'mpc-ndvi-layer',
  boundaryFill: 'mpc-boundary-fill',
  boundaryOutline: 'mpc-boundary-outline',
  clipMask: 'mpc-clip-mask-layer',
} as const;

// ============================================================================
// ADD MPC LAYERS
// ============================================================================

export function addMPCLayers(
  map: maplibregl.Map,
  data: MPCNLPResponse['data']
): void {
  console.log('[MPC] Adding MPC visualization layers...');

  // Remove any existing MPC layers first
  removeMPCLayers(map);

  const { bbox, collection, images, boundary } = data;

  if (!bbox || bbox.length !== 4) {
    console.warn('[MPC] Invalid bbox:', bbox);
    return;
  }

  const color = getCollectionColor(collection);

  // ═════════════════════════════════════════════════════════════════════════
  // 1. CITY BOUNDARY (if available) OR SEARCH AREA
  // ═════════════════════════════════════════════════════════════════════════

  if (boundary) {
    console.log('[MPC] Adding city boundary outline...');

    map.addSource(MPC_SOURCE_IDS.boundary, {
      type: 'geojson',
      data: {
        type: 'Feature',
        properties: { name: data.location },
        geometry: boundary,
      },
    });

    // Boundary fill (semi-transparent)
    map.addLayer({
      id: MPC_LAYER_IDS.boundaryFill,
      type: 'fill',
      source: MPC_SOURCE_IDS.boundary,
      paint: {
        'fill-color': color,
        'fill-opacity': 0.1,
      },
    });

    // Boundary outline (solid line)
    map.addLayer({
      id: MPC_LAYER_IDS.boundaryOutline,
      type: 'line',
      source: MPC_SOURCE_IDS.boundary,
      paint: {
        'line-color': color,
        'line-width': 3,
        'line-opacity': 0.8,
      },
    });

    console.log('[MPC] ✅ Added boundary outline');
  } else {
    // Fallback: Search area box (dashed)
    console.log('[MPC] Adding search area box (no boundary found)...');

    const searchPolygon: GeoJSON.Feature = {
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [bbox[0], bbox[1]], // SW
            [bbox[2], bbox[1]], // SE
            [bbox[2], bbox[3]], // NE
            [bbox[0], bbox[3]], // NW
            [bbox[0], bbox[1]], // Close
          ],
        ],
      },
    };

    map.addSource(MPC_SOURCE_IDS.searchArea, {
      type: 'geojson',
      data: {
        type: 'FeatureCollection',
        features: [searchPolygon],
      },
    });

    map.addLayer({
      id: MPC_LAYER_IDS.searchArea,
      type: 'line',
      source: MPC_SOURCE_IDS.searchArea,
      paint: {
        'line-color': color,
        'line-width': 2,
        'line-dasharray': [5, 3],
        'line-opacity': 0.8,
      },
    });

    console.log('[MPC] ✅ Added search area box');
  }

  // ═════════════════════════════════════════════════════════════════════════
  // 2. AUTO-ZOOM TO FIT BOUNDARY
  // ═════════════════════════════════════════════════════════════════════════

  if (boundary) {
    try {
      // Fit map to boundary with padding
      const bounds = new maplibregl.LngLatBounds();

      boundary.coordinates[0].forEach((coord: number[]) => {
        bounds.extend(coord as [number, number]);
      });

      map.fitBounds(bounds, {
        padding: { top: 50, bottom: 50, left: 400, right: 50 }, // Account for sidebar
        duration: 2000,
        maxZoom: 12,
      });

      console.log('[MPC] ✅ Auto-zoomed to boundary');
    } catch (error) {
      console.error('[MPC] Failed to auto-zoom:', error);
      // Fallback to center/zoom
      flyToMPCLocation(map, data.center, data.zoom);
    }
  } else {
    // Fallback: Use provided center and zoom
    flyToMPCLocation(map, data.center, data.zoom);
  }

  // ═════════════════════════════════════════════════════════════════════════
  // 3. SATELLITE IMAGERY (Natural Color by default)
  // ═════════════════════════════════════════════════════════════════════════

  if (images && images.length > 0) {
    // Get best image (lowest cloud cover)
    const bestImage = images.reduce((best, img) => {
      const bestCloud = best.cloud_cover ?? 100;
      const imgCloud = img.cloud_cover ?? 100;
      return imgCloud < bestCloud ? img : best;
    });

    console.log('[MPC] Best image:', bestImage.id, `(${bestImage.cloud_cover}% clouds)`);

    // Add Natural Color imagery by default
    if (bestImage.tile_urls?.natural_color) {
      const tileUrl = bestImage.tile_urls.natural_color;

      map.addSource(MPC_SOURCE_IDS.imagery, {
        type: 'raster',
        tiles: [tileUrl],
        tileSize: 256,
        minzoom: 8,
        maxzoom: 18,
      });

      map.addLayer(
        {
          id: MPC_LAYER_IDS.naturalColor,
          type: 'raster',
          source: MPC_SOURCE_IDS.imagery,
          paint: {
            'raster-opacity': 0.9,
            'raster-fade-duration': 0, // Instant rendering for better performance
          },
        },
        boundary ? MPC_LAYER_IDS.boundaryFill : undefined // Add below boundary if exists
      );

      console.log('[MPC] ✅ Added Natural Color imagery layer');

      // ═══════════════════════════════════════════════════════════════════
      // CLIP MASK: Hide imagery outside boundary
      // Creates inverted polygon (world with boundary as hole)
      // ═══════════════════════════════════════════════════════════════════

      if (boundary && boundary.coordinates && boundary.coordinates[0]) {
        console.log('[MPC] Adding clip mask to hide imagery outside boundary...');

        // Create world polygon with boundary as a hole
        const worldPolygon: number[][] = [
          [-180, -85],
          [180, -85],
          [180, 85],
          [-180, 85],
          [-180, -85],
        ];

        // Get boundary coordinates (reversed for hole)
        const boundaryCoords = boundary.coordinates[0];
        const reversedBoundary = [...boundaryCoords].reverse();

        // Create inverted mask: world polygon with boundary hole
        const invertedMaskGeoJSON: GeoJSON.Feature = {
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'Polygon',
            coordinates: [worldPolygon, reversedBoundary],
          },
        };

        map.addSource(MPC_SOURCE_IDS.clipMask, {
          type: 'geojson',
          data: invertedMaskGeoJSON,
        });

        // Add mask layer above imagery - matches basemap background
        map.addLayer({
          id: MPC_LAYER_IDS.clipMask,
          type: 'fill',
          source: MPC_SOURCE_IDS.clipMask,
          paint: {
            'fill-color': '#0a0f1a', // Dark basemap color
            'fill-opacity': 1,
          },
        });

        console.log('[MPC] ✅ Added clip mask - imagery clipped to boundary');
      }
    }

    // ═════════════════════════════════════════════════════════════════════
    // 4. IMAGE COUNT MARKER
    // ═════════════════════════════════════════════════════════════════════

    const centerLon = (bbox[0] + bbox[2]) / 2;
    const centerLat = (bbox[1] + bbox[3]) / 2;

    const markerDiv = document.createElement('div');
    markerDiv.className = 'mpc-image-marker'; // For easy cleanup
    markerDiv.style.cssText = `
      background: ${color};
      color: white;
      border-radius: 50%;
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 14px;
      border: 3px solid white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      cursor: pointer;
    `;
    markerDiv.textContent = images.length.toString();
    markerDiv.title = `${images.length} image(s) available`;

    new maplibregl.Marker({ element: markerDiv })
      .setLngLat([centerLon, centerLat])
      .addTo(map);

    console.log('[MPC] ✅ Added image count marker');
  }

  console.log('[MPC] ✅ All MPC layers added successfully');
}

// ============================================================================
// REMOVE MPC LAYERS
// ============================================================================

export function removeMPCLayers(map: maplibregl.Map): void {
  console.log('[MPC] Removing MPC layers...');

  // Remove all MPC layers
  Object.values(MPC_LAYER_IDS).forEach((layerId) => {
    if (map.getLayer(layerId)) {
      try {
        map.removeLayer(layerId);
        console.log(`[MPC] Removed layer: ${layerId}`);
      } catch (error) {
        console.warn(`[MPC] Failed to remove layer ${layerId}:`, error);
      }
    }
  });

  // Remove all MPC sources
  Object.values(MPC_SOURCE_IDS).forEach((sourceId) => {
    if (map.getSource(sourceId)) {
      try {
        map.removeSource(sourceId);
        console.log(`[MPC] Removed source: ${sourceId}`);
      } catch (error) {
        console.warn(`[MPC] Failed to remove source ${sourceId}:`, error);
      }
    }
  });

  // Remove image count markers
  const markers = document.querySelectorAll('.mpc-image-marker');
  markers.forEach((marker) => {
    try {
      marker.remove();
      console.log('[MPC] Removed marker');
    } catch (error) {
      console.warn('[MPC] Failed to remove marker:', error);
    }
  });

  console.log('[MPC] ✅ All MPC layers removed');
}

// ============================================================================
// SWITCH MPC LAYER (Natural Color / False Color / NDVI)
// ============================================================================

export function switchMPCLayer(
  map: maplibregl.Map,
  layerType: 'natural_color' | 'false_color' | 'ndvi',
  images: MPCImage[]
): void {
  console.log(`[MPC] Switching to ${layerType} layer`);

  if (!images || images.length === 0) {
    console.warn('[MPC] No images available');
    return;
  }

  // Get best image (lowest cloud cover)
  const bestImage = images.reduce((best, img) => {
    const bestCloud = best.cloud_cover ?? 100;
    const imgCloud = img.cloud_cover ?? 100;
    return imgCloud < bestCloud ? img : best;
  });

  const tileUrl = bestImage.tile_urls?.[layerType];

  if (!tileUrl) {
    console.warn(`[MPC] No tile URL for ${layerType}`);
    return;
  }

  // Remove existing imagery layers
  [
    MPC_LAYER_IDS.naturalColor,
    MPC_LAYER_IDS.falseColor,
    MPC_LAYER_IDS.ndvi,
  ].forEach((layerId) => {
    if (map.getLayer(layerId)) {
      map.removeLayer(layerId);
    }
  });

  // Remove imagery source
  if (map.getSource(MPC_SOURCE_IDS.imagery)) {
    map.removeSource(MPC_SOURCE_IDS.imagery);
  }

  // Add new source
  map.addSource(MPC_SOURCE_IDS.imagery, {
    type: 'raster',
    tiles: [tileUrl],
    tileSize: 256,
    minzoom: 8,
    maxzoom: 18,
  });

  // Add new layer
  const layerIdMap = {
    natural_color: MPC_LAYER_IDS.naturalColor,
    false_color: MPC_LAYER_IDS.falseColor,
    ndvi: MPC_LAYER_IDS.ndvi,
  };

  // Place imagery below clip mask (if exists) for clipping to work
  let beforeLayer: string | undefined = undefined;
  if (map.getLayer(MPC_LAYER_IDS.clipMask)) {
    beforeLayer = MPC_LAYER_IDS.clipMask;
  } else if (map.getLayer(MPC_LAYER_IDS.boundaryFill)) {
    beforeLayer = MPC_LAYER_IDS.boundaryFill;
  }

  map.addLayer(
    {
      id: layerIdMap[layerType],
      type: 'raster',
      source: MPC_SOURCE_IDS.imagery,
      paint: {
        'raster-opacity': 0.9,
        'raster-fade-duration': 0, // Instant for better performance
      },
    },
    beforeLayer
  );

  console.log(`[MPC] ✅ Switched to ${layerType}`);
}

// ============================================================================
// FLY TO MPC LOCATION
// ============================================================================

export function flyToMPCLocation(
  map: maplibregl.Map,
  center: [number, number],
  zoom: number
): void {
  console.log('[MPC] Flying to location:', center, 'zoom:', zoom);

  map.flyTo({
    center,
    zoom,
    duration: 2000,
    essential: true,
  });
}

// ============================================================================
// CHECK IF MPC LAYERS EXIST
// ============================================================================

export function hasMPCLayers(map: maplibregl.Map): boolean {
  return Object.values(MPC_LAYER_IDS).some((layerId) => map.getLayer(layerId));
}

// ============================================================================
// EXPORTS
// ============================================================================

export { MPC_SOURCE_IDS, MPC_LAYER_IDS };