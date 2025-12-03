/**
 * GEOWISE Map Container
 * Main MapLibre GL JS map component with layer management
 */

'use client';

import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { LayerState, GeoJSONFeatureCollection } from '@/services/types';

interface MapContainerProps {
  layers: LayerState[];
  fireData?: GeoJSONFeatureCollection;
  forestTileUrl?: string;
  mpcData?: GeoJSONFeatureCollection;
  onMapLoad?: (map: maplibregl.Map) => void;
}

export default function MapContainer({
  layers,
  fireData,
  forestTileUrl,
  mpcData,
  onMapLoad,
}: MapContainerProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const initMap = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          'osm-tiles': {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution:
              '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
          },
        },
        layers: [
          {
            id: 'osm-tiles-layer',
            type: 'raster',
            source: 'osm-tiles',
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: [
        Number(process.env.NEXT_PUBLIC_DEFAULT_CENTER_LON) || 69.3451,
        Number(process.env.NEXT_PUBLIC_DEFAULT_CENTER_LAT) || 30.3753,
      ],
      zoom: Number(process.env.NEXT_PUBLIC_DEFAULT_ZOOM) || 5,
    });

    // Add navigation controls
    initMap.addControl(new maplibregl.NavigationControl(), 'top-right');

    // Add scale control
    initMap.addControl(
      new maplibregl.ScaleControl({ unit: 'metric' }),
      'bottom-left'
    );

    initMap.on('load', () => {
      console.log('[Map] Loaded successfully');
      setMapLoaded(true);
      if (onMapLoad) onMapLoad(initMap);
    });

    map.current = initMap;

    return () => {
      map.current?.remove();
    };
  }, [onMapLoad]);

  // Add GFW Forest Loss Tiles
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    const forestLayer = layers.find((l) => l.id === 'forest-loss');
    if (!forestLayer) return;

    const sourceId = 'gfw-forest-loss';
    const layerId = 'gfw-forest-loss-layer';

    if (forestLayer.visible) {
      // Add source if not exists
      if (!map.current.getSource(sourceId)) {
        map.current.addSource(sourceId, {
          type: 'raster',
          tiles: [
            'https://tiles.globalforestwatch.org/umd_tree_cover_loss/v1.9/tcd_30/{z}/{x}/{y}.png',
          ],
          tileSize: 256,
          minzoom: 3,
          maxzoom: 12,
        });

        map.current.addLayer({
          id: layerId,
          type: 'raster',
          source: sourceId,
          paint: {
            'raster-opacity': forestLayer.opacity,
          },
        });

        console.log('[Map] Added GFW forest loss layer');
      }
    } else {
      // Remove layer and source if hidden
      if (map.current.getLayer(layerId)) {
        map.current.removeLayer(layerId);
      }
      if (map.current.getSource(sourceId)) {
        map.current.removeSource(sourceId);
      }
    }
  }, [mapLoaded, layers]);

  // Add Fire Points (GeoJSON)
  useEffect(() => {
    if (!map.current || !mapLoaded || !fireData) return;

    const fireLayer = layers.find((l) => l.id === 'fires');
    if (!fireLayer) return;

    const sourceId = 'fire-points';
    const layerId = 'fire-points-layer';
    const clusterLayerId = 'fire-clusters-layer';
    const clusterCountLayerId = 'fire-cluster-count-layer';

    if (fireLayer.visible) {
      // Add source if not exists
      if (!map.current.getSource(sourceId)) {
        map.current.addSource(sourceId, {
          type: 'geojson',
          data: fireData,
          cluster: true,
          clusterMaxZoom: 14,
          clusterRadius: 50,
        });

        // Clustered points
        map.current.addLayer({
          id: clusterLayerId,
          type: 'circle',
          source: sourceId,
          filter: ['has', 'point_count'],
          paint: {
            'circle-color': [
              'step',
              ['get', 'point_count'],
              '#FED976',
              100,
              '#FEB24C',
              750,
              '#FD8D3C',
              1000,
              '#FC4E2A',
              2000,
              '#E31A1C',
              5000,
              '#BD0026',
            ],
            'circle-radius': ['step', ['get', 'point_count'], 20, 100, 30, 750, 40],
            'circle-opacity': fireLayer.opacity,
          },
        });

        // Cluster count labels
        map.current.addLayer({
          id: clusterCountLayerId,
          type: 'symbol',
          source: sourceId,
          filter: ['has', 'point_count'],
          layout: {
            'text-field': '{point_count_abbreviated}',
            'text-font': ['Open Sans Bold'],
            'text-size': 12,
          },
          paint: {
            'text-color': '#ffffff',
          },
        });

        // Unclustered points
        map.current.addLayer({
          id: layerId,
          type: 'circle',
          source: sourceId,
          filter: ['!', ['has', 'point_count']],
          paint: {
            'circle-color': fireLayer.color,
            'circle-radius': 6,
            'circle-stroke-width': 1,
            'circle-stroke-color': '#fff',
            'circle-opacity': fireLayer.opacity,
          },
        });

        // Add popup on click
        map.current.on('click', layerId, (e) => {
          if (!e.features || !e.features[0]) return;

          const coordinates = (
            e.features[0].geometry as any
          ).coordinates.slice();
          const props = e.features[0].properties;

          new maplibregl.Popup()
            .setLngLat(coordinates)
            .setHTML(
              `
              <div class="p-2">
                <h3 class="font-bold text-sm mb-1">Fire Detection</h3>
                <p class="text-xs">FRP: ${props?.frp || 'N/A'} MW</p>
                <p class="text-xs">Confidence: ${props?.confidence || 'N/A'}</p>
                <p class="text-xs">Date: ${props?.acq_date || 'N/A'}</p>
              </div>
            `
            )
            .addTo(map.current!);
        });

        map.current.on('mouseenter', layerId, () => {
          map.current!.getCanvas().style.cursor = 'pointer';
        });

        map.current.on('mouseleave', layerId, () => {
          map.current!.getCanvas().style.cursor = '';
        });

        console.log('[Map] Added fire points layer');
      } else {
        // Update data
        const source = map.current.getSource(sourceId) as maplibregl.GeoJSONSource;
        source.setData(fireData as any);
      }
    } else {
      // Remove layers
      [clusterLayerId, clusterCountLayerId, layerId].forEach((lid) => {
        if (map.current!.getLayer(lid)) {
          map.current!.removeLayer(lid);
        }
      });
      if (map.current.getSource(sourceId)) {
        map.current.removeSource(sourceId);
      }
    }
  }, [mapLoaded, layers, fireData]);

  // Add MPC Land Use Data
  useEffect(() => {
    if (!map.current || !mapLoaded || !mpcData) return;

    const mpcLayer = layers.find((l) => l.id === 'mpc-land-use');
    if (!mpcLayer || !mpcLayer.visible) return;

    const sourceId = 'mpc-land-use';
    const layerId = 'mpc-land-use-layer';

    if (!map.current.getSource(sourceId)) {
      map.current.addSource(sourceId, {
        type: 'geojson',
        data: mpcData,
      });

      map.current.addLayer({
        id: layerId,
        type: 'fill',
        source: sourceId,
        paint: {
          'fill-color': ['get', 'color'],
          'fill-opacity': mpcLayer.opacity,
        },
      });

      console.log('[Map] Added MPC land use layer');
    }
  }, [mapLoaded, layers, mpcData]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} className="absolute inset-0" />

      {/* Loading indicator */}
      {!mapLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
          <div className="text-white text-lg">Loading map...</div>
        </div>
      )}
    </div>
  );
}