import { Map } from 'maplibre-gl';
import type { SurfaceWaterResponse, WaterTiles, WaterLayerState, WaterLayerOpacity } from '@/types/water';

const WATER_LAYER_IDS = {
    occurrence: 'water-occurrence-layer',
    change: 'water-change-layer',
    seasonality: 'water-seasonality-layer',
    recurrence: 'water-recurrence-layer',
    transitions: 'water-transitions-layer',
};

const WATER_SOURCE_IDS = {
    occurrence: 'water-occurrence-source',
    change: 'water-change-source',
    seasonality: 'water-seasonality-source',
    recurrence: 'water-recurrence-source',
    transitions: 'water-transitions-source',
};

// Store tiles globally for year switching
let globalWaterTiles: WaterTiles | null = null;
let currentWaterYear: number | null = null;

/**
 * Add all water layers to the map
 */
export function addWaterLayers(
    map: Map,
    data: SurfaceWaterResponse,
    layers: WaterLayerState,
    opacity: WaterLayerOpacity
): void {
    const tiles = data.tiles;

    if (!tiles) {
        console.error('[Water] No tile URLs in response');
        return;
    }

    console.log('[Water] Adding layers with tiles:', Object.keys(tiles));

    // Store tiles globally
    globalWaterTiles = tiles;

    // Remove existing layers first
    removeWaterLayers(map);

    // Add main analysis layers
    if (tiles.water_occurrence?.url) {
        addRasterLayer(map, WATER_SOURCE_IDS.occurrence, WATER_LAYER_IDS.occurrence,
            tiles.water_occurrence.url, opacity.waterOccurrence, layers.waterOccurrence);
    }

    if (tiles.current_water?.url) {
        addRasterLayer(map, WATER_SOURCE_IDS.change, WATER_LAYER_IDS.change,
            tiles.current_water.url, opacity.waterChange, layers.waterChange);
    }

    if (tiles.lost_water?.url) {
        addRasterLayer(map, WATER_SOURCE_IDS.seasonality, WATER_LAYER_IDS.seasonality,
            tiles.lost_water.url, opacity.waterSeasonality, layers.waterSeasonality);
    }

    if (tiles.new_water?.url) {
        addRasterLayer(map, WATER_SOURCE_IDS.recurrence, WATER_LAYER_IDS.recurrence,
            tiles.new_water.url, opacity.waterRecurrence, layers.waterRecurrence);
    }

    if (tiles.max_extent?.url) {
        addRasterLayer(map, WATER_SOURCE_IDS.transitions, WATER_LAYER_IDS.transitions,
            tiles.max_extent.url, opacity.waterTransitions, layers.waterTransitions);
    }

    console.log('[Water] ✅ All layers added');
}

/**
 * Helper to add a raster layer
 */
function addRasterLayer(
    map: Map,
    sourceId: string,
    layerId: string,
    tileUrl: string,
    opacity: number,
    visible: boolean
): void {
    if (!map.getSource(sourceId)) {
        map.addSource(sourceId, {
            type: 'raster',
            tiles: [tileUrl],
            tileSize: 256,
        });
    }

    if (!map.getLayer(layerId)) {
        map.addLayer({
            id: layerId,
            type: 'raster',
            source: sourceId,
            paint: {
                'raster-opacity': opacity,
                'raster-fade-duration': 0,
            },
            layout: {
                visibility: visible ? 'visible' : 'none',
            },
        });
    }
}

/**
 * Remove all water layers from the map
 */
export function removeWaterLayers(map: Map): void {
    Object.values(WATER_LAYER_IDS).forEach((layerId) => {
        if (map.getLayer(layerId)) {
            map.removeLayer(layerId);
        }
    });

    Object.values(WATER_SOURCE_IDS).forEach((sourceId) => {
        if (map.getSource(sourceId)) {
            map.removeSource(sourceId);
        }
    });

    // Reset global state
    globalWaterTiles = null;
    currentWaterYear = null;

    console.log('[Water] Layers removed');
}

/**
 * Toggle a specific water layer visibility
 */
export function toggleWaterLayer(
    map: Map,
    layerId: string,
    visible: boolean
): void {
    if (map.getLayer(layerId)) {
        map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
        console.log(`[Water] Layer ${layerId} visibility: ${visible}`);
    }
}

/**
 * Update water layer opacity
 */
export function updateWaterLayerOpacity(
    map: Map,
    layerId: string,
    opacity: number
): void {
    if (map.getLayer(layerId)) {
        map.setPaintProperty(layerId, 'raster-opacity', opacity);
    }
}

/**
 * Easing function for smooth animation
 */
function easeInOutCubic(t: number): number {
    return t < 0.5
        ? 4 * t * t * t
        : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/**
 * Smooth crossfade transition between years
 * Note: Timeline animation has been removed - this is a no-op
 */
export function smoothWaterTransition(
    map: Map,
    fromYear: number,
    toYear: number,
    duration: number = 500
): void {
    console.log('[Water] Timeline animation not implemented');
}

/**
 * Fly to water body location
 */
export function flyToWaterLocation(
    map: Map,
    center: [number, number],
    zoom: number
): void {
    map.flyTo({
        center: center,
        zoom: zoom,
        duration: 2000,
        essential: true
    });
}

/**
 * Get available years from tiles
 * Note: Timeline animation has been removed - returns empty array
 */
export function getWaterAvailableYears(tiles: WaterTiles): number[] {
    return [];
}
