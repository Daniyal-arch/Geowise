/**
 * Flood Map Layers Utility - v5.2 FIXED
 * Handles adding/removing flood layers to MapLibre GL map
 * Location: frontend/src/utils/floodMapLayers.ts
 * 
 * FIX: Correct layer ID mapping for opacity updates
 */

import maplibregl from 'maplibre-gl';
import type { FloodTiles, FloodLayerState, FloodLayerOpacity } from '@/types/flood';

// ============================================================================
// LAYER IDS - SINGLE SOURCE OF TRUTH
// ============================================================================

export const FLOOD_LAYER_IDS: Record<string, string> = {
  // SAR layers
  floodExtent: 'flood-extent-layer',
  changeDetection: 'flood-change-detection-layer',
  sarBefore: 'flood-sar-before-layer',
  sarAfter: 'flood-sar-after-layer',
  permanentWater: 'flood-permanent-water-layer',
  // Optical layers
  opticalBefore: 'flood-optical-before-layer',
  opticalAfter: 'flood-optical-after-layer',
  falseColor: 'flood-false-color-layer',
  ndwi: 'flood-ndwi-layer',
};

export const FLOOD_SOURCE_IDS: Record<string, string> = {
  // SAR layers
  floodExtent: 'flood-extent-source',
  changeDetection: 'flood-change-detection-source',
  sarBefore: 'flood-sar-before-source',
  sarAfter: 'flood-sar-after-source',
  permanentWater: 'flood-permanent-water-source',
  // Optical layers
  opticalBefore: 'flood-optical-before-source',
  opticalAfter: 'flood-optical-after-source',
  falseColor: 'flood-false-color-source',
  ndwi: 'flood-ndwi-source',
};

// Map layer keys to tile keys
const LAYER_TO_TILE_KEY: Record<string, keyof FloodTiles> = {
  floodExtent: 'flood_extent',
  changeDetection: 'change_detection',
  sarBefore: 'sar_before',
  sarAfter: 'sar_after',
  permanentWater: 'permanent_water',
  opticalBefore: 'optical_before',
  opticalAfter: 'optical_after',
  falseColor: 'false_color_after',
  ndwi: 'ndwi_after',
};

// ============================================================================
// HELPER: Add Raster Layer
// ============================================================================

function addRasterLayer(
  map: maplibregl.Map,
  sourceId: string,
  layerId: string,
  tileUrl: string,
  opacity: number
): void {
  // Remove existing if present
  if (map.getLayer(layerId)) {
    map.removeLayer(layerId);
  }
  if (map.getSource(sourceId)) {
    map.removeSource(sourceId);
  }

  // Add source
  map.addSource(sourceId, {
    type: 'raster',
    tiles: [tileUrl],
    tileSize: 256,
  });

  // Add layer
  map.addLayer({
    id: layerId,
    type: 'raster',
    source: sourceId,
    paint: {
      'raster-opacity': opacity,
    },
  });
  
  console.log(`[FloodMap] Added layer: ${layerId} (opacity: ${opacity})`);
}

// ============================================================================
// ADD FLOOD LAYERS (SAR only - initial load)
// ============================================================================

export function addFloodLayers(
  map: maplibregl.Map,
  tiles: FloodTiles,
  layers: FloodLayerState,
  opacity: FloodLayerOpacity
): void {
  console.log('[FloodMap] Adding SAR flood layers...');

  // Remove existing SAR layers first (not optical)
  const sarLayerKeys = ['floodExtent', 'changeDetection', 'sarBefore', 'sarAfter', 'permanentWater'];
  
  sarLayerKeys.forEach((key) => {
    const layerId = FLOOD_LAYER_IDS[key];
    const sourceId = FLOOD_SOURCE_IDS[key];
    if (map.getLayer(layerId)) map.removeLayer(layerId);
    if (map.getSource(sourceId)) map.removeSource(sourceId);
  });

  // Add layers in order (bottom to top)
  const layerOrder = ['sarBefore', 'sarAfter', 'permanentWater', 'changeDetection', 'floodExtent'];
  
  layerOrder.forEach((key) => {
    const tileKey = LAYER_TO_TILE_KEY[key] as keyof FloodTiles;
    const tileUrl = tiles[tileKey];
    
    if (tileUrl) {
      const layerKey = key as keyof FloodLayerState;
      const opacityKey = key as keyof FloodLayerOpacity;
      const isVisible = layers[layerKey];
      const layerOpacity = isVisible ? opacity[opacityKey] : 0;
      
      addRasterLayer(
        map,
        FLOOD_SOURCE_IDS[key],
        FLOOD_LAYER_IDS[key],
        tileUrl,
        layerOpacity
      );
    }
  });

  console.log('[FloodMap] ✅ SAR flood layers added');
}

// ============================================================================
// ADD OPTICAL LAYERS (v5.2 - on-demand)
// ============================================================================

export function addOpticalLayers(
  map: maplibregl.Map,
  opticalTiles: {
    optical_before?: string;
    optical_after?: string;
    false_color_after?: string;
    ndwi_after?: string;
  },
  layers?: FloodLayerState,
  opacity?: FloodLayerOpacity
): void {
  console.log('[FloodMap] 🛰️ Adding optical layers...');

  const opticalLayerOrder = ['opticalBefore', 'opticalAfter', 'falseColor', 'ndwi'];
  
  opticalLayerOrder.forEach((key) => {
    const tileKey = LAYER_TO_TILE_KEY[key];
    const tileUrl = opticalTiles[tileKey as keyof typeof opticalTiles];
    
    if (tileUrl) {
      // Default: opticalAfter visible, others hidden
      let layerOpacity = 0;
      if (key === 'opticalAfter') {
        layerOpacity = opacity?.opticalAfter ?? 0.8;
      } else if (layers && opacity) {
        const layerKey = key as keyof FloodLayerState;
        const opacityKey = key as keyof FloodLayerOpacity;
        layerOpacity = layers[layerKey] ? opacity[opacityKey] : 0;
      }
      
      addRasterLayer(
        map,
        FLOOD_SOURCE_IDS[key],
        FLOOD_LAYER_IDS[key],
        tileUrl,
        layerOpacity
      );
    }
  });

  console.log('[FloodMap] ✅ Optical layers added');
}

// ============================================================================
// REMOVE FLOOD LAYERS
// ============================================================================

export function removeFloodLayers(map: maplibregl.Map): void {
  console.log('[FloodMap] Removing all flood layers...');

  Object.keys(FLOOD_LAYER_IDS).forEach((key) => {
    const layerId = FLOOD_LAYER_IDS[key];
    const sourceId = FLOOD_SOURCE_IDS[key];
    
    if (map.getLayer(layerId)) {
      map.removeLayer(layerId);
    }
    if (map.getSource(sourceId)) {
      map.removeSource(sourceId);
    }
  });

  console.log('[FloodMap] ✅ All flood layers removed');
}

// ============================================================================
// UPDATE LAYER VISIBILITY - FIXED
// ============================================================================

export function updateFloodLayerVisibility(
  map: maplibregl.Map,
  tiles: FloodTiles,
  layer: keyof FloodLayerState,
  visible: boolean,
  opacity: number
): void {
  const layerId = FLOOD_LAYER_IDS[layer];
  const sourceId = FLOOD_SOURCE_IDS[layer];
  const tileKey = LAYER_TO_TILE_KEY[layer];
  const tileUrl = tiles[tileKey as keyof FloodTiles];

  if (!layerId || !tileUrl) {
    console.log(`[FloodMap] Skip visibility update: ${layer} (no layer/tile)`);
    return;
  }

  // Check if layer exists on map
  if (!map.getLayer(layerId)) {
    // Layer doesn't exist, create it if visible
    if (visible && tileUrl) {
      addRasterLayer(map, sourceId, layerId, tileUrl, opacity);
    }
    return;
  }

  // Update opacity (0 = hidden, opacity value = visible)
  const newOpacity = visible ? opacity : 0;
  map.setPaintProperty(layerId, 'raster-opacity', newOpacity);
  console.log(`[FloodMap] Updated ${layer} visibility: ${visible}, opacity: ${newOpacity}`);
}

// ============================================================================
// UPDATE LAYER OPACITY - FIXED
// ============================================================================

export function updateFloodLayerOpacity(
  map: maplibregl.Map,
  layer: keyof FloodLayerOpacity,
  opacity: number
): void {
  const layerId = FLOOD_LAYER_IDS[layer];

  if (!layerId) {
    console.warn(`[FloodMap] Unknown layer key: ${layer}`);
    return;
  }

  if (map.getLayer(layerId)) {
    map.setPaintProperty(layerId, 'raster-opacity', opacity);
    console.log(`[FloodMap] Updated ${layer} (${layerId}) opacity: ${opacity}`);
  } else {
    console.log(`[FloodMap] Layer not on map: ${layerId}`);
  }
}

// ============================================================================
// FLY TO FLOOD LOCATION
// ============================================================================

export function flyToFloodLocation(
  map: maplibregl.Map,
  center: [number, number],
  zoom: number
): void {
  console.log('[FloodMap] Flying to flood location:', center, 'zoom:', zoom);

  map.flyTo({
    center,
    zoom,
    duration: 2000,
    essential: true,
  });
}

// ============================================================================
// CHECK IF FLOOD LAYERS EXIST
// ============================================================================

export function hasFloodLayers(map: maplibregl.Map): boolean {
  return Object.values(FLOOD_LAYER_IDS).some((layerId) => map.getLayer(layerId));
}

// ============================================================================
// GET ACTIVE FLOOD LAYERS
// ============================================================================

export function getActiveFloodLayers(map: maplibregl.Map): string[] {
  return Object.entries(FLOOD_LAYER_IDS)
    .filter(([_, layerId]) => map.getLayer(layerId))
    .map(([key, _]) => key);
}