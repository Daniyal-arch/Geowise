/**
 * Air Quality Map Layer Utilities
 * Handles adding, removing, and toggling Sentinel-5P air quality layers
 */

import maplibregl from 'maplibre-gl';
import { AirQualityResponse, AQLayerState, AQLayerOpacity } from '@/types/airQuality';

// ============================================================================
// ADD AIR QUALITY LAYERS
// ============================================================================

export function addAirQualityLayers(
    map: maplibregl.Map,
    data: AirQualityResponse,
    layerState: AQLayerState,
    layerOpacity: AQLayerOpacity
): void {
    console.log('[AirQuality] Adding air quality layers');

    if (!data.tiles) {
        console.warn('[AirQuality] No tiles data available');
        return;
    }

    // Add each pollutant layer
    Object.entries(data.tiles).forEach(([pollutantKey, tileData]) => {
        try {
            const sourceId = `aq-${pollutantKey.toLowerCase()}-source`;
            const layerId = `aq-${pollutantKey.toLowerCase()}-layer`;

            // Add source
            if (!map.getSource(sourceId)) {
                map.addSource(sourceId, {
                    type: 'raster',
                    tiles: [tileData.url],
                    tileSize: 256,
                });
                console.log(`[AirQuality] Added source: ${sourceId}`);
            }

            // Add layer
            if (!map.getLayer(layerId)) {
                const isVisible = layerState[pollutantKey as keyof AQLayerState] ?? false;
                const opacity = layerOpacity[pollutantKey as keyof AQLayerOpacity] ?? 0.7;

                map.addLayer({
                    id: layerId,
                    type: 'raster',
                    source: sourceId,
                    paint: {
                        'raster-opacity': isVisible ? opacity : 0,
                        'raster-fade-duration': 300,
                    },
                    layout: {
                        visibility: isVisible ? 'visible' : 'none'
                    }
                });
                console.log(`[AirQuality] Added layer: ${layerId}, visible: ${isVisible}`);
            }
        } catch (error) {
            console.error(`[AirQuality] Error adding layer ${pollutantKey}:`, error);
        }
    });
}

// ============================================================================
// REMOVE AIR QUALITY LAYERS
// ============================================================================

export function removeAirQualityLayers(map: maplibregl.Map): void {
    console.log('[AirQuality] Removing air quality layers');

    const pollutants = ['no2', 'so2', 'co', 'o3', 'ch4', 'hcho', 'aerosol'];

    pollutants.forEach((pollutant) => {
        const sourceId = `aq-${pollutant}-source`;
        const layerId = `aq-${pollutant}-layer`;

        try {
            // Remove layer
            if (map.getLayer(layerId)) {
                map.removeLayer(layerId);
                console.log(`[AirQuality] Removed layer: ${layerId}`);
            }

            // Remove source
            if (map.getSource(sourceId)) {
                map.removeSource(sourceId);
                console.log(`[AirQuality] Removed source: ${sourceId}`);
            }
        } catch (error) {
            console.error(`[AirQuality] Error removing ${pollutant}:`, error);
        }
    });
}

// ============================================================================
// TOGGLE LAYER VISIBILITY
// ============================================================================

export function toggleAirQualityLayer(
    map: maplibregl.Map,
    pollutantKey: string,
    visible: boolean
): void {
    const layerId = `aq-${pollutantKey.toLowerCase()}-layer`;

    try {
        if (map.getLayer(layerId)) {
            map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
            console.log(`[AirQuality] Toggled ${pollutantKey}: ${visible}`);
        }
    } catch (error) {
        console.error(`[AirQuality] Error toggling ${pollutantKey}:`, error);
    }
}

// ============================================================================
// UPDATE LAYER OPACITY
// ============================================================================

export function updateAirQualityOpacity(
    map: maplibregl.Map,
    pollutantKey: string,
    opacity: number
): void {
    const layerId = `aq-${pollutantKey.toLowerCase()}-layer`;

    try {
        if (map.getLayer(layerId)) {
            map.setPaintProperty(layerId, 'raster-opacity', opacity);
            console.log(`[AirQuality] Updated ${pollutantKey} opacity: ${opacity}`);
        }
    } catch (error) {
        console.error(`[AirQuality] Error updating opacity for ${pollutantKey}:`, error);
    }
}

// ============================================================================
// HELPER: CHECK IF AQ LAYERS EXIST
// ============================================================================

export function hasAirQualityLayers(map: maplibregl.Map): boolean {
    return map.getLayer('aq-no2-layer') !== undefined;
}
