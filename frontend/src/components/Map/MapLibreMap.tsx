'use client';

import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

interface MapLibreMapProps {
  onMapLoad?: (map: maplibregl.Map) => void;
}

export default function MapLibreMap({ onMapLoad }: MapLibreMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [currentBasemap, setCurrentBasemap] = useState<'satellite' | 'streets' | 'terrain' | 'dark'>('satellite');

  // Basemap styles
  const basemapStyles = {
    satellite: {
      version: 8,
      sources: {
        'satellite': {
          type: 'raster',
          tiles: [
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
          ],
          tileSize: 256,
          attribution: '© Esri'
        }
      },
      layers: [
        {
          id: 'satellite-layer',
          type: 'raster',
          source: 'satellite',
          minzoom: 0,
          maxzoom: 22
        }
      ]
    },
    streets: {
      version: 8,
      sources: {
        'osm': {
          type: 'raster',
          tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
          tileSize: 256,
          attribution: '© OpenStreetMap contributors'
        }
      },
      layers: [
        {
          id: 'osm-layer',
          type: 'raster',
          source: 'osm',
          minzoom: 0,
          maxzoom: 19
        }
      ]
    },
    terrain: {
      version: 8,
      sources: {
        'terrain': {
          type: 'raster',
          tiles: [
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}'
          ],
          tileSize: 256,
          attribution: '© Esri'
        }
      },
      layers: [
        {
          id: 'terrain-layer',
          type: 'raster',
          source: 'terrain',
          minzoom: 0,
          maxzoom: 13
        }
      ]
    },
    dark: {
      version: 8,
      sources: {
        'dark': {
          type: 'raster',
          tiles: [
            'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png'
          ],
          tileSize: 256,
          attribution: '© Stadia Maps'
        }
      },
      layers: [
        {
          id: 'dark-layer',
          type: 'raster',
          source: 'dark',
          minzoom: 0,
          maxzoom: 20
        }
      ]
    }
  };

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const initMap = new maplibregl.Map({
      container: mapContainer.current,
      style: basemapStyles[currentBasemap] as any,
      center: [-55.0, -10.0], // Brazil center
      zoom: 4,
      attributionControl: true,
    });

    // Add navigation controls (zoom buttons)
    initMap.addControl(
      new maplibregl.NavigationControl({
        showCompass: true,
        showZoom: true,
        visualizePitch: true
      }),
      'top-right'
    );

    // Add scale control
    initMap.addControl(
      new maplibregl.ScaleControl({
        maxWidth: 100,
        unit: 'metric'
      }),
      'bottom-left'
    );

    initMap.on('load', () => {
      console.log('[MapLibre] Map loaded successfully');
      setMapLoaded(true);
      if (onMapLoad) onMapLoad(initMap);
    });

    map.current = initMap;

    return () => {
      map.current?.remove();
    };
  }, []);

  // Change basemap
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    map.current.setStyle(basemapStyles[currentBasemap] as any);
  }, [currentBasemap, mapLoaded]);

  // Expose basemap change function globally
  useEffect(() => {
    (window as any).changeBasemap = (type: 'satellite' | 'streets' | 'terrain' | 'dark') => {
      setCurrentBasemap(type);
    };
  }, []);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} className="absolute inset-0" />
      
      {!mapLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-75 z-10">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-300">Loading map...</p>
          </div>
        </div>
      )}
    </div>
  );
}