/**
 * Hansen Forest Change Dataset Utilities
 * WITH DRIVER LAYER SUPPORT
 * Dataset-specific logic for UMD Hansen Global Forest Change + Curtis Drivers
 * Location: frontend/src/services/datasets/hansenForest.ts
 */

import type { HansenForestTiles, DriverTiles, LayerVisibility, LayerOpacity } from '@/types/gee';
import type { Map as MapLibreMap } from 'maplibre-gl';

/**
 * Default layer visibility settings (UPDATED with drivers)
 */
export const DEFAULT_VISIBILITY: LayerVisibility = {
  baseline: true,   // Show tree cover by default
  loss: true,       // Show deforestation by default
  gain: false,      // Hide gain by default (sparse data)
  drivers: false    // 🟢 NEW: Hide drivers by default (shown on query)
};

/**
 * Default layer opacity settings (UPDATED with drivers)
 */
export const DEFAULT_OPACITY: LayerOpacity = {
  baseline: 0.6,  // 60% - Let basemap show through
  loss: 0.8,      // 80% - Emphasize deforestation
  gain: 0.3,      // 30% - Subtle (sparse data)
  drivers: 0.7    // 🟢 NEW: 70% - Visible but not overwhelming
};

/**
 * Layer metadata for UI rendering (UPDATED with drivers)
 */
export const LAYER_METADATA = {
  baseline: {
    name: 'Forest Density',
    description: 'Forest density baseline from year 2000',
    color: 'green',
    gradient: 'from-green-300 to-green-500',
    yearRange: 'Baseline 2000'
  },
  loss: {
    name: 'Tree Cover Loss',
    description: 'Tree cover loss 2001-2024',
    color: 'red',
    gradient: 'from-red-400 to-red-600',
    yearRange: '2001-2024'
  },
  gain: {
    name: 'Forest Gain',
    description: 'Forest regrowth 2000-2012',
    color: 'blue',
    gradient: 'from-blue-400 to-blue-600',
    yearRange: '2000-2012'
  },
  drivers: {
    name: 'Loss Drivers',
    description: 'Deforestation drivers & causes',
    color: 'orange',
    gradient: 'from-orange-400 to-red-600',
    yearRange: '2001-2015'
  }
};

/**
 * Add Hansen layers to MapLibre map
 */
export function addHansenLayers(
  map: MapLibreMap,
  tilesData: HansenForestTiles,
  visibility: LayerVisibility,
  opacity: LayerOpacity
): void {
  console.log('[Hansen] Adding layers to map...');

  // BASELINE LAYER
  if (!map.getSource('gee-baseline')) {
    map.addSource('gee-baseline', {
      type: 'raster',
      tiles: [tilesData.layers.baseline.tile_url],
      tileSize: 256
    });

    map.addLayer({
      id: 'gee-baseline-layer',
      type: 'raster',
      source: 'gee-baseline',
      paint: {
        'raster-opacity': opacity.baseline
      },
      layout: {
        visibility: visibility.baseline ? 'visible' : 'none'
      }
    });

    console.log('[Hansen] ✅ Baseline layer added');
  }

  // LOSS LAYER
  if (!map.getSource('gee-loss')) {
    map.addSource('gee-loss', {
      type: 'raster',
      tiles: [tilesData.layers.loss.tile_url],
      tileSize: 256
    });

    map.addLayer({
      id: 'gee-loss-layer',
      type: 'raster',
      source: 'gee-loss',
      paint: {
        'raster-opacity': opacity.loss
      },
      layout: {
        visibility: visibility.loss ? 'visible' : 'none'
      }
    });

    console.log('[Hansen] ✅ Loss layer added');
  }

  // GAIN LAYER
  if (!map.getSource('gee-gain')) {
    map.addSource('gee-gain', {
      type: 'raster',
      tiles: [tilesData.layers.gain.tile_url],
      tileSize: 256
    });

    map.addLayer({
      id: 'gee-gain-layer',
      type: 'raster',
      source: 'gee-gain',
      paint: {
        'raster-opacity': opacity.gain
      },
      layout: {
        visibility: visibility.gain ? 'visible' : 'none'
      }
    });

    console.log('[Hansen] ✅ Gain layer added');
  }
}

/**
 * 🟢 NEW: Add driver layer to map
 */
export function addDriverLayer(
  map: MapLibreMap,
  driverData: DriverTiles,
  opacity: number = 0.7,
  visible: boolean = true
): void {
  console.log('[Drivers] Adding driver layer to map...');

  // Remove existing driver layer if present
  if (map.getLayer('gee-drivers-layer')) {
    map.removeLayer('gee-drivers-layer');
  }
  if (map.getSource('gee-drivers')) {
    map.removeSource('gee-drivers');
  }

  // Add driver source
  map.addSource('gee-drivers', {
    type: 'raster',
    tiles: [driverData.tile_url],
    tileSize: 256
  });

  // Add driver layer
  map.addLayer({
    id: 'gee-drivers-layer',
    type: 'raster',
    source: 'gee-drivers',
    paint: {
      'raster-opacity': opacity
    },
    layout: {
      visibility: visible ? 'visible' : 'none'
    }
  });

  console.log('[Drivers] ✅ Driver layer added');
}

/**
 * 🟢 NEW: Remove driver layer from map
 */
export function removeDriverLayer(map: MapLibreMap): void {
  if (map.getLayer('gee-drivers-layer')) {
    map.removeLayer('gee-drivers-layer');
  }
  if (map.getSource('gee-drivers')) {
    map.removeSource('gee-drivers');
  }
  console.log('[Drivers] ✅ Driver layer removed');
}

/**
 * Remove Hansen layers from map
 */
export function removeHansenLayers(map: MapLibreMap): void {
  const layers = ['gee-baseline-layer', 'gee-loss-layer', 'gee-gain-layer'];
  const sources = ['gee-baseline', 'gee-loss', 'gee-gain'];

  layers.forEach(layerId => {
    if (map.getLayer(layerId)) {
      map.removeLayer(layerId);
    }
  });

  sources.forEach(sourceId => {
    if (map.getSource(sourceId)) {
      map.removeSource(sourceId);
    }
  });

  console.log('[Hansen] ✅ All layers removed');
}

/**
 * Update layer visibility
 */
export function updateLayerVisibility(
  map: MapLibreMap,
  layer: keyof LayerVisibility,
  visible: boolean
): void {
  const layerId = `gee-${layer}-layer`;
  
  if (map.getLayer(layerId)) {
    map.setLayoutProperty(
      layerId,
      'visibility',
      visible ? 'visible' : 'none'
    );
    console.log(`[Hansen] ${layer} visibility:`, visible);
  }
}

/**
 * Update layer opacity
 */
export function updateLayerOpacity(
  map: MapLibreMap,
  layer: keyof LayerOpacity,
  opacity: number
): void {
  const layerId = `gee-${layer}-layer`;
  
  if (map.getLayer(layerId)) {
    map.setPaintProperty(layerId, 'raster-opacity', opacity);
    console.log(`[Hansen] ${layer} opacity:`, opacity);
  }
}

/**
 * Check if Hansen layers exist on map
 */
export function hasHansenLayers(map: MapLibreMap): boolean {
  return Boolean(
    map.getLayer('gee-baseline-layer') ||
    map.getLayer('gee-loss-layer') ||
    map.getLayer('gee-gain-layer')
  );
}

/**
 * 🟢 NEW: Check if driver layer exists on map
 */
export function hasDriverLayer(map: MapLibreMap): boolean {
  return Boolean(map.getLayer('gee-drivers-layer'));
}