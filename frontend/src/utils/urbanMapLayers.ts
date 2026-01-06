import { Map } from 'maplibre-gl';
import { UrbanExpansionResponse } from '../types/urban';

// Store tiles globally for switchToYear function
let globalUrbanTiles: any = null;
let currentAnimationYear: number | null = null;

/**
 * Add Urbanization Layers to MapLibre
 */
export const addUrbanLayers = (map: Map, data: UrbanExpansionResponse) => {
    // v5.3 FIX: Backend sends 'tiles', frontend type expects 'tile_urls'
    const tiles = data.tile_urls || (data as any).tiles;

    if (!map || !tiles) {
        console.warn('Urban layers: No tiles found in data', data);
        return;
    }

    // Store tiles globally for year switching
    globalUrbanTiles = tiles;

    // 1. Urbanization Timeline Layer (When each pixel became urban)
    if (tiles.urbanization_timeline) {
        if (map.getSource('urban-timeline-source')) {
            (map.getSource('urban-timeline-source') as any).setTiles([tiles.urbanization_timeline]);
        } else {
            map.addSource('urban-timeline-source', {
                type: 'raster',
                tiles: [tiles.urbanization_timeline],
                tileSize: 256,
            });

            map.addLayer({
                id: 'urban-timeline-layer',
                type: 'raster',
                source: 'urban-timeline-source',
                paint: {
                    'raster-opacity': 0.8,
                    'raster-fade-duration': 300
                },
                layout: {
                    visibility: 'visible'
                }
            });
        }
    }

    // Create separate layers for each year for smooth crossfade animation
    const availableYears = getAvailableYears(tiles);

    availableYears.forEach((year, index) => {
        const yearTile = tiles[`built_${year}`];

        if (yearTile) {
            const sourceId = `urban-built-source-${year}`;
            const layerId = `urban-built-${year}`;

            if (!map.getSource(sourceId)) {
                const isInitialYear = index === availableYears.length - 1;

                map.addSource(sourceId, {
                    type: 'raster',
                    tiles: [yearTile],
                    tileSize: 256,
                });

                // Add layer - initial year should be visible with opacity 0.8
                map.addLayer({
                    id: layerId,
                    type: 'raster',
                    source: sourceId,
                    paint: {
                        'raster-opacity': isInitialYear ? 0.8 : 0,
                        'raster-fade-duration': 0, // We control opacity for smooth transitions
                    },
                    layout: {
                        visibility: isInitialYear ? 'visible' : 'none'
                    }
                });

                console.log(`[UrbanMap] Created layer: ${layerId} (${isInitialYear ? 'INITIAL - visible' : 'hidden'})`, {
                    tileUrl: yearTile.substring(0, 100) + '...',
                    opacity: isInitialYear ? 0.8 : 0,
                    visibility: isInitialYear ? 'visible' : 'none'
                });
            }
        }
    });

    // Set the initial year as visible and hide the timeline layer
    if (availableYears.length > 0) {
        const initialYear = availableYears[availableYears.length - 1];
        const initialLayerId = `urban-built-${initialYear}`;
        if (map.getLayer(initialLayerId)) {
            map.setLayoutProperty(initialLayerId, 'visibility', 'visible');
            map.setPaintProperty(initialLayerId, 'raster-opacity', 0.8);
            currentAnimationYear = initialYear;

            console.log(`[UrbanMap] Initial layer set: ${initialLayerId} (opacity: 0.8, visible: true)`);

            // Hide the timeline layer since we're using year-specific layers
            if (map.getLayer('urban-timeline-layer')) {
                map.setLayoutProperty('urban-timeline-layer', 'visibility', 'none');
            }
        }
    }

    // 2. Built-up Surface (Latest)
    if (tiles.built_up) {
        if (map.getSource('urban-built-source')) {
            (map.getSource('urban-built-source') as any).setTiles([tiles.built_up]);
        } else {
            map.addSource('urban-built-source', {
                type: 'raster',
                tiles: [tiles.built_up],
                tileSize: 256,
            });

            map.addLayer({
                id: 'urban-built-layer',
                type: 'raster',
                source: 'urban-built-source',
                paint: {
                    'raster-opacity': 0.0, // Hidden by default, toggleable
                },
                layout: {
                    visibility: 'none'
                }
            });
        }
    }

    // 3. New Urban Areas (Growth Layer)
    if (tiles.growth_layer) {
        if (map.getSource('urban-growth-source')) {
            (map.getSource('urban-growth-source') as any).setTiles([tiles.growth_layer]);
        } else {
            map.addSource('urban-growth-source', {
                type: 'raster',
                tiles: [tiles.growth_layer],
                tileSize: 256,
            });

            map.addLayer({
                id: 'urban-growth-layer',
                type: 'raster',
                source: 'urban-growth-source',
                paint: {
                    'raster-opacity': 0, // Hidden by default
                },
                layout: {
                    visibility: 'none'
                }
            });
        }
    }
};

/**
 * Toggle Urban Layer Visibility
 */
export const toggleUrbanLayer = (map: Map, layerId: string, isVisible: boolean, opacity: number = 0.8) => {
    if (!map.getLayer(layerId)) return;

    const visibility = isVisible ? 'visible' : 'none';
    map.setLayoutProperty(layerId, 'visibility', visibility);
    map.setPaintProperty(layerId, 'raster-opacity', isVisible ? opacity : 0);
};

/**
 * Switch the map to show a specific year's urban layer with smooth cross-fade
 */
export const switchToYear = (map: Map, year: number) => {
    // Check if we have tiles
    if (!globalUrbanTiles) {
        console.log('[UrbanMap] Urban data not loaded yet');
        return;
    }

    // Get the tile URL for this specific year
    const yearTileKey = `built_${year}`;
    const yearTileUrl = globalUrbanTiles[yearTileKey];

    if (!yearTileUrl) {
        console.warn('[UrbanMap] No tile found for year:', year);
        return;
    }

    // Skip if same year
    if (currentAnimationYear === year) {
        return;
    }

    // Use the timeline layer for smooth animation
    const sourceId = 'urban-timeline-source';
    const layerId = 'urban-timeline-layer';

    if (!map.getSource(sourceId) || !map.getLayer(layerId)) {
        console.log('[UrbanMap] Timeline layer not ready');
        return;
    }

    // Smooth transition: fade out, switch tiles, fade in
    const transitionDuration = 400; // ms

    // Step 1: Fade out current layer
    map.setPaintProperty(layerId, 'raster-opacity', 0);

    // Step 2: After fade out, switch tiles
    setTimeout(() => {
        (map.getSource(sourceId) as any).setTiles([yearTileUrl]);

        // Step 3: Immediately fade in with new tiles
        setTimeout(() => {
            map.setPaintProperty(layerId, 'raster-opacity', 0.8);
            currentAnimationYear = year;
        }, 50); // Small delay to ensure tiles start loading
    }, transitionDuration);

    console.log('[UrbanMap] Smoothly switching to year:', year);
};

/**
 * Easing function for smooth animation
 */
function easeInOutCubic(t: number): number {
    return t < 0.5
        ? 4 * t * t * t
        : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/**
 * Smoothly transition between years with crossfade effect
 */
export const smoothTransitionToYear = (map: Map, fromYear: number, toYear: number, duration: number = 500): void => {
    // Check if we have tiles
    if (!globalUrbanTiles) {
        console.log('[UrbanMap] Urban data not loaded yet');
        return;
    }

    const availableYears = getAvailableYears(globalUrbanTiles);

    // Find closest available years
    const closestFrom = availableYears.reduce((prev, curr) =>
        Math.abs(curr - fromYear) < Math.abs(prev - fromYear) ? curr : prev
    );
    const closestTo = availableYears.reduce((prev, curr) =>
        Math.abs(curr - toYear) < Math.abs(prev - toYear) ? curr : prev
    );

    const fromLayerId = `urban-built-${closestFrom}`;
    const toLayerId = `urban-built-${closestTo}`;

    // If same layer, skip
    if (closestFrom === closestTo) {
        currentAnimationYear = closestTo;
        return;
    }

    // Make sure both layers exist
    if (!map.getLayer(fromLayerId) || !map.getLayer(toLayerId)) {
        console.warn('[UrbanMap] Layer not found:', fromLayerId, toLayerId);
        return;
    }

    // Show the target layer but at 0 opacity
    map.setLayoutProperty(toLayerId, 'visibility', 'visible');
    map.setPaintProperty(toLayerId, 'raster-opacity', 0);

    // Animate the crossfade
    const startTime = performance.now();

    function animate(currentTime: number) {
        // Check if map still exists (component might have unmounted)
        if (!map || !map.getLayer(fromLayerId) || !map.getLayer(toLayerId)) {
            console.warn('[UrbanMap] Animation cancelled: map or layers no longer available');
            return;
        }

        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Ease function for smoother animation
        const eased = easeInOutCubic(progress);

        // Crossfade: from layer fades out, to layer fades in
        // Clamp to prevent floating-point precision errors causing negative values
        const fromOpacity = Math.max(0, Math.min(0.8, 0.8 * (1 - eased)));
        const toOpacity = Math.max(0, Math.min(0.8, 0.8 * eased));

        try {
            map.setPaintProperty(fromLayerId, 'raster-opacity', fromOpacity);
            map.setPaintProperty(toLayerId, 'raster-opacity', toOpacity);

            // Log every 100ms to debug
            if (Math.floor(elapsed / 100) !== Math.floor((elapsed - 16) / 100)) {
                console.log(`[UrbanMap] Animation progress: ${(progress * 100).toFixed(0)}% | ${fromLayerId}: ${fromOpacity.toFixed(3)} → ${toLayerId}: ${toOpacity.toFixed(3)}`);
            }
        } catch (error) {
            console.warn('[UrbanMap] Animation error:', error);
            return;
        }

        if (progress < 1) {
            requestAnimationFrame(animate);
        } else {
            // Animation complete - hide the old layer
            try {
                map.setLayoutProperty(fromLayerId, 'visibility', 'none');
                map.setPaintProperty(fromLayerId, 'raster-opacity', 0);
                map.setPaintProperty(toLayerId, 'raster-opacity', 0.8);
                currentAnimationYear = closestTo;
            } catch (error) {
                console.warn('[UrbanMap] Animation cleanup error:', error);
            }
        }
    }

    requestAnimationFrame(animate);
    console.log(`[UrbanMap] Smooth crossfade: ${closestFrom} → ${closestTo} (${duration}ms)`);
};

/**
 * Get available years from the tile data
 */
export const getAvailableYears = (tiles: any): number[] => {
    const years: number[] = [];

    // Check for tiles in the format built_YYYY
    Object.keys(tiles).forEach(key => {
        if (key.startsWith('built_') && key !== 'built_up') {
            const year = parseInt(key.replace('built_', ''));
            if (!isNaN(year)) {
                years.push(year);
            }
        }
    });

    return years.sort((a, b) => a - b);
};

/**
 * Remove all urban layers
 */
export const removeUrbanLayers = (map: Map) => {
    // Remove base layers
    const baseLayers = [
        'urban-timeline-layer',
        'urban-built-layer',
        'urban-growth-layer'
    ];
    baseLayers.forEach(layer => {
        if (map.getLayer(layer)) map.removeLayer(layer);
    });

    // Remove year-specific layers
    if (globalUrbanTiles) {
        const availableYears = getAvailableYears(globalUrbanTiles);
        availableYears.forEach(year => {
            const layerId = `urban-built-${year}`;
            if (map.getLayer(layerId)) {
                map.removeLayer(layerId);
            }
        });
    }

    // Remove base sources
    const baseSources = [
        'urban-timeline-source',
        'urban-built-source',
        'urban-growth-source'
    ];
    baseSources.forEach(source => {
        if (map.getSource(source)) map.removeSource(source);
    });

    // Remove year-specific sources
    if (globalUrbanTiles) {
        const availableYears = getAvailableYears(globalUrbanTiles);
        availableYears.forEach(year => {
            const sourceId = `urban-built-source-${year}`;
            if (map.getSource(sourceId)) {
                map.removeSource(sourceId);
            }
        });
    }

    // Reset animation state
    globalUrbanTiles = null;
    currentAnimationYear = null;
};
