// utils/urbanMapLayers.ts

import maplibregl from 'maplibre-gl';
import type { UrbanExpansionResponse } from '@/types/urban';

const URBAN_LAYER_IDS = {
    timeline: 'urban-timeline-layer',
    builtUp: 'urban-built-layer',
    growth: 'urban-growth-layer',
    // Year-specific layers
    built1975: 'urban-built-1975',
    built1990: 'urban-built-1990',
    built2000: 'urban-built-2000',
    built2015: 'urban-built-2015',
    built2020: 'urban-built-2020',
};

const URBAN_SOURCE_IDS = {
    timeline: 'urban-timeline-source',
    builtUp: 'urban-built-source',
    growth: 'urban-growth-source',
    built1975: 'urban-built-1975-source',
    built1990: 'urban-built-1990-source',
    built2000: 'urban-built-2000-source',
    built2015: 'urban-built-2015-source',
    built2020: 'urban-built-2020-source',
};

/**
 * Add all urban expansion layers to the map
 */
export function addUrbanLayers(
    map: maplibregl.Map,
    data: UrbanExpansionResponse
): void {
    const tiles = data.tile_urls || (data as any).tiles;
    
    if (!tiles) {
        console.error('[Urban] No tile URLs in response');
        return;
    }

    console.log('[Urban] Adding layers with tiles:', Object.keys(tiles));

    // Remove existing layers first
    removeUrbanLayers(map);

    // Add Timeline Layer (default visible)
    if (tiles.urbanization_timeline) {
        addRasterLayer(map, URBAN_SOURCE_IDS.timeline, URBAN_LAYER_IDS.timeline, tiles.urbanization_timeline, 0.8, true);
    }

    // Add Built-up Layer (hidden by default)
    if (tiles.built_up) {
        addRasterLayer(map, URBAN_SOURCE_IDS.builtUp, URBAN_LAYER_IDS.builtUp, tiles.built_up, 0.7, false);
    }

    // Add Growth Layer (hidden by default)
    if (tiles.growth_layer) {
        addRasterLayer(map, URBAN_SOURCE_IDS.growth, URBAN_LAYER_IDS.growth, tiles.growth_layer, 0.8, false);
    }

    // Add Year-Specific Layers (all hidden, used for animation)
    const yearLayers = [
        { year: 1975, sourceId: URBAN_SOURCE_IDS.built1975, layerId: URBAN_LAYER_IDS.built1975 },
        { year: 1990, sourceId: URBAN_SOURCE_IDS.built1990, layerId: URBAN_LAYER_IDS.built1990 },
        { year: 2000, sourceId: URBAN_SOURCE_IDS.built2000, layerId: URBAN_LAYER_IDS.built2000 },
        { year: 2015, sourceId: URBAN_SOURCE_IDS.built2015, layerId: URBAN_LAYER_IDS.built2015 },
        { year: 2020, sourceId: URBAN_SOURCE_IDS.built2020, layerId: URBAN_LAYER_IDS.built2020 },
    ];

    yearLayers.forEach(({ year, sourceId, layerId }) => {
        const tileUrl = tiles[`built_${year}`];
        if (tileUrl) {
            addRasterLayer(map, sourceId, layerId, tileUrl, 0.8, false);
            console.log(`[Urban] Added layer for ${year}`);
        }
    });

    console.log('[Urban] ✅ All layers added');
}

/**
 * Helper to add a raster layer
 */
function addRasterLayer(
    map: maplibregl.Map,
    sourceId: string,
    layerId: string,
    tileUrl: string,
    opacity: number,
    visible: boolean
): void {
    // Add source if not exists
    if (!map.getSource(sourceId)) {
        map.addSource(sourceId, {
            type: 'raster',
            tiles: [tileUrl],
            tileSize: 256,
        });
    }

    // Add layer if not exists
    if (!map.getLayer(layerId)) {
        map.addLayer({
            id: layerId,
            type: 'raster',
            source: sourceId,
            paint: {
                'raster-opacity': opacity,
            },
            layout: {
                visibility: visible ? 'visible' : 'none',
            },
        });
    }
}

/**
 * Remove all urban layers from the map
 */
export function removeUrbanLayers(map: maplibregl.Map): void {
    // Remove all layers
    Object.values(URBAN_LAYER_IDS).forEach((layerId) => {
        if (map.getLayer(layerId)) {
            map.removeLayer(layerId);
        }
    });

    // Remove all sources
    Object.values(URBAN_SOURCE_IDS).forEach((sourceId) => {
        if (map.getSource(sourceId)) {
            map.removeSource(sourceId);
        }
    });

    console.log('[Urban] Layers removed');
}

/**
 * Toggle a specific urban layer visibility
 */
export function toggleUrbanLayer(
    map: maplibregl.Map,
    layerId: string,
    visible: boolean
): void {
    if (map.getLayer(layerId)) {
        map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
        console.log(`[Urban] Layer ${layerId} visibility: ${visible}`);
    }
}

/**
 * Switch to a specific year's built-up layer (for timeline animation)
 */
export function switchToYear(map: maplibregl.Map, year: number): void {
    // Map year to closest available epoch
    const availableYears = [1975, 1990, 2000, 2015, 2020];
    const closestYear = availableYears.reduce((prev, curr) =>
        Math.abs(curr - year) < Math.abs(prev - year) ? curr : prev
    );

    console.log(`[Urban] Switching to year ${year} (closest: ${closestYear})`);

    // Hide all year layers
    availableYears.forEach((y) => {
        const layerId = `urban-built-${y}`;
        if (map.getLayer(layerId)) {
            map.setLayoutProperty(layerId, 'visibility', 'none');
        }
    });

    // Show the selected year layer
    const targetLayerId = `urban-built-${closestYear}`;
    if (map.getLayer(targetLayerId)) {
        map.setLayoutProperty(targetLayerId, 'visibility', 'visible');
        console.log(`[Urban] ✅ Showing layer: ${targetLayerId}`);
    } else {
        console.warn(`[Urban] Layer not found: ${targetLayerId}`);
    }
}

/**
 * Get available years from tile URLs
 */
export function getAvailableYears(tiles: Record<string, string | undefined>): number[] {
    const years: number[] = [];
    
    [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020].forEach((year) => {
        if (tiles[`built_${year}`]) {
            years.push(year);
        }
    });

    return years.length > 0 ? years : [1975, 1990, 2000, 2015, 2020];
}