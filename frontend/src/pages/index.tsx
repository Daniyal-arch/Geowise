'use client';

import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { getCountryData, detectCountryFromQuery, getCountryName } from '@/utils/countryCoordinates';
import { getCountryBoundary } from '@/services/boundaries';
import { DEFAULT_BOUNDARY_STYLE } from '@/types/gee';
// Add after existing imports
import { getLiveFireDetections } from '@/services/fireService';
import type { FireStatistics } from '@/types/fires';
import { FireStatsPanel } from '@/components/FireStatsPanel';
// GEE imports
import { getHansenForestTiles, getDriverTiles } from '@/services/geeService';
import {
  addHansenLayers,
  removeHansenLayers,
  updateLayerVisibility,
  addDriverLayer,
  removeDriverLayer,
  hasDriverLayer
} from '@/services/datasets/hansenForest';
import type { LayerVisibility, DriverTiles } from '@/types/gee';
// ============================================================================
// 🛰️ MPC MODULE IMPORTS
// ============================================================================
import { MPCStatsPanel } from '@/components/MPCStatsPanel';
import {
  addMPCLayers,
  removeMPCLayers,
  flyToMPCLocation
} from '@/utils/mpcMapLayers';
import type { MPCNLPResponse } from '@/types/mpc';
import { getCollectionColor } from '@/types/mpc';

// ============================================================================
// 🌊 FLOOD MODULE IMPORTS
// ============================================================================
import { FloodStatsPanel } from '@/components/FloodStatsPanel';
import { FloodLayerControls } from '@/components/FloodLayerControls';
import {
  addFloodLayers,
  removeFloodLayers,
  updateFloodLayerVisibility,
  updateFloodLayerOpacity,
  flyToFloodLocation,
  addOpticalLayers
} from '@/utils/floodMapLayers';
import type {
  FloodNLPResponse,
  FloodLayerState,
  FloodLayerOpacity,
  FloodTiles
} from '@/types/flood';
import { DEFAULT_FLOOD_LAYERS, DEFAULT_FLOOD_OPACITY } from '@/types/flood';

// ============================================================================
// 💨 AIR QUALITY MODULE IMPORTS
// ============================================================================
import AirQualityStatsPanel from '@/components/airquality/AirQualityStatsPanel';
import AirQualityLayerControl from '@/components/airquality/AirQualityLayerControl';
import {
  addAirQualityLayers,
  removeAirQualityLayers,
  toggleAirQualityLayer,
  updateAirQualityOpacity,
  hasAirQualityLayers
} from '@/utils/airQualityMapLayers';
import type { AirQualityResponse, AQLayerState, AQLayerOpacity } from '@/types/airQuality';
import { DEFAULT_AQ_LAYERS, DEFAULT_AQ_OPACITY } from '@/types/airQuality';

// ============================================================================
// 🏙️ URBAN MODULE IMPORTS
// ============================================================================
import UrbanStatsPanel from '@/components/urban/UrbanStatsPanel';
import UrbanTimelineSlider from '@/components/urban/UrbanTimelineSlider';
import UrbanLayerControl from '@/components/urban/UrbanLayerControl';
import WaterTimelineSlider from '@/components/water/WaterTimelineSlider';
import {
  addUrbanLayers,
  removeUrbanLayers,
  toggleUrbanLayer,
  switchToYear,
  getAvailableYears,
  smoothTransitionToYear
} from '@/utils/urbanMapLayers';
import type { UrbanExpansionResponse } from '@/types/urban';

// ============================================================================
// 💧 WATER MODULE IMPORTS
// ============================================================================
import WaterStatsPanel from '@/components/water/WaterStatsPanel';
import WaterLayerControl from '@/components/water/WaterLayerControl';
import {
  addWaterLayers,
  removeWaterLayers,
  toggleWaterLayer,
  updateWaterLayerOpacity,
  flyToWaterLocation
} from '@/utils/waterMapLayers';
import type { SurfaceWaterResponse, WaterLayerState, WaterLayerOpacity } from '@/types/water';
import { DEFAULT_WATER_LAYERS, DEFAULT_WATER_OPACITY } from '@/types/water';


export default function Dashboard() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  const [currentCountry, setCurrentCountry] = useState<string>('BRA');
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'assistant', content: string }[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [isLoadingQuery, setIsLoadingQuery] = useState(false);
  const [isChatExpanded, setIsChatExpanded] = useState(false);
  const [hasQueried, setHasQueried] = useState(false);

  // ============================================================================
  // 🛰️ MPC STATE
  // ============================================================================
  const [mpcData, setMpcData] = useState<MPCNLPResponse['data'] | null>(null);

  const [availableLayers, setAvailableLayers] = useState<string[]>([]);

  const [visibleLayers, setVisibleLayers] = useState<LayerVisibility>({
    baseline: false,
    loss: false,
    gain: false,
    drivers: false
  });

  //  Stats panel toggle
  const [showStatsPanel, setShowStatsPanel] = useState(true);

  //  Driver layer data
  const [driverLayerData, setDriverLayerData] = useState<DriverTiles | null>(null);

  const [fireStats, setFireStats] = useState<FireStatistics | null>(null);

  // ============================================================================
  // 🌊 FLOOD STATE
  // ============================================================================
  const [floodData, setFloodData] = useState<FloodNLPResponse['data'] | null>(null);
  const [floodLayers, setFloodLayers] = useState<FloodLayerState>(DEFAULT_FLOOD_LAYERS);
  const [floodOpacity, setFloodOpacity] = useState<FloodLayerOpacity>(DEFAULT_FLOOD_OPACITY);

  // ============================================================================
  // 🏙️ URBAN STATE
  // ============================================================================
  const [urbanData, setUrbanData] = useState<UrbanExpansionResponse | null>(null);
  const [urbanTimelineYear, setUrbanTimelineYear] = useState<number>(2020);
  const [previousUrbanYear, setPreviousUrbanYear] = useState<number>(2020);
  const [isUrbanPlaying, setIsUrbanPlaying] = useState(false);
  const [urbanAvailableYears, setUrbanAvailableYears] = useState<number[]>([1975, 1990, 2000, 2015, 2020]);
  const [showUrbanGif, setShowUrbanGif] = useState(false);
  const [urbanLayers, setUrbanLayers] = useState({
    urbanization_timeline: true,
    built_up: false,
    growth_layer: false
  });

  // ============================================================================
  // 💧 WATER STATE
  // ============================================================================
  const [waterData, setWaterData] = useState<SurfaceWaterResponse | null>(null);
  const [waterLayers, setWaterLayers] = useState<WaterLayerState>(DEFAULT_WATER_LAYERS);
  const [waterOpacity, setWaterOpacity] = useState<WaterLayerOpacity>(DEFAULT_WATER_OPACITY);
  const [showWaterGif, setShowWaterGif] = useState(false);
  const [waterTimelineYear, setWaterTimelineYear] = useState<number>(2021);
  const [previousWaterYear, setPreviousWaterYear] = useState<number>(2021);
  const [isWaterPlaying, setIsWaterPlaying] = useState(false);
  const [waterAvailableYears, setWaterAvailableYears] = useState<number[]>([]);

  // ============================================================================
  // 💨 AIR QUALITY STATE
  // ============================================================================
  const [airQualityData, setAirQualityData] = useState<AirQualityResponse | null>(null);
  const [aqLayers, setAqLayers] = useState<AQLayerState>(DEFAULT_AQ_LAYERS);
  const [aqOpacity, setAqOpacity] = useState<AQLayerOpacity>(DEFAULT_AQ_OPACITY);

  // Helper: Flatten coordinates for bbox calculation
  const flattenCoordinates = (coords: any): number[][] => {
    if (!coords) return [];
    const result: number[][] = [];
    const flatten = (arr: any) => {
      if (typeof arr[0] === 'number') {
        result.push(arr);
      } else if (Array.isArray(arr)) {
        arr.forEach((item: any) => flatten(item));
      }
    };
    flatten(coords);
    return result;
  };

  //  Boundary layer tracking  
  const [showBoundary, setShowBoundary] = useState(false);
  const BOUNDARY_SOURCE_ID = 'country-boundary-source';
  const BOUNDARY_FILL_ID = 'country-boundary-fill';
  const BOUNDARY_LINE_ID = 'country-boundary-line';

  const [forestStats, setForestStats] = useState<{
    totalLoss: number;
    recentYear: number;
    recentLoss: number;
    trend: string;
    severity: string;
    changePercent: number;
    peakYear: number;
    peakLoss: number;
    lowestYear: number;
    lowestLoss: number;
    yearlyData: Array<{ year: number, loss: number }>;
    recentAvg: number;
    earlyAvg: number;
    yearsAvailable: number;
    dataRange: string;
    dataDescription: string;
  } | null>(null);

  const [driverBreakdown, setDriverBreakdown] = useState<Array<{
    driver_category: string;
    loss_ha: number;
    percentage: number;
    pixel_count: number;
  }> | null>(null);


  const basemapStyle = {
    version: 8,
    sources: {
      'carto-dark': {
        type: 'raster',
        tiles: ['https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: '©OpenStreetMap, ©CartoDB'
      }
    },
    layers: [{
      id: 'dark-layer',
      type: 'raster',
      source: 'carto-dark',
      minzoom: 0,
      maxzoom: 20
    }]
  };

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    try {
      const initMap = new maplibregl.Map({
        container: mapContainer.current,
        style: basemapStyle as any,
        center: [-51.93, -14.24],
        zoom: 3,
        attributionControl: true,
        pixelRatio: window.devicePixelRatio || 2,
      });

      initMap.addControl(new maplibregl.NavigationControl(), 'top-right');
      initMap.addControl(new maplibregl.ScaleControl({}), 'bottom-left');

      initMap.on('load', () => {
        setMapLoaded(true);
      });

      map.current = initMap;
    } catch (error) {
      console.error('[Map] Error:', error);
      setMapLoaded(true);
    }

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    Object.keys(visibleLayers).forEach((layer) => {
      const layerKey = layer as keyof LayerVisibility;
      updateLayerVisibility(map.current!, layerKey, visibleLayers[layerKey]);
    });
  }, [visibleLayers, mapLoaded]);

  // ============================================================================
  // 🌊 FLOOD LAYER VISIBILITY EFFECT - v5.2 FIXED
  // ============================================================================
  useEffect(() => {
    if (!map.current || !mapLoaded || !floodData?.tiles) return;

    const allLayerKeys = Object.keys(floodLayers) as (keyof FloodLayerState)[];

    allLayerKeys.forEach((layerKey) => {
      updateFloodLayerVisibility(
        map.current!,
        floodData.tiles,
        layerKey,
        floodLayers[layerKey],
        floodOpacity[layerKey]
      );
    });
  }, [floodLayers, floodOpacity, mapLoaded, floodData]);

  // ============================================================================
  // 🌊 FLOOD OPACITY EFFECT - v5.2 FIXED
  // ============================================================================
  useEffect(() => {
    if (!map.current || !mapLoaded || !floodData?.tiles) return;

    const allOpacityKeys = Object.keys(floodOpacity) as (keyof FloodLayerOpacity)[];

    allOpacityKeys.forEach((layerKey) => {
      const stateKey = layerKey as keyof FloodLayerState;
      if (floodLayers[stateKey]) {
        updateFloodLayerOpacity(map.current!, layerKey, floodOpacity[layerKey]);
      }
    });
  }, [floodOpacity, floodLayers, mapLoaded, floodData]);

  // ============================================================================
  // 🏙️ URBAN LAYER EFFECT
  // ============================================================================
  useEffect(() => {
    if (!map.current || !mapLoaded || !urbanData) return;

    // Toggle base layers based on state
    // NOTE: We keep timeline layer OFF because we use year-specific layers for animation
    toggleUrbanLayer(map.current, 'urban-built-layer', urbanLayers.built_up);
    toggleUrbanLayer(map.current, 'urban-growth-layer', urbanLayers.growth_layer);

  }, [urbanLayers, mapLoaded, urbanData]);

  // ============================================================================
  // 🏙️ URBAN TIMELINE YEAR CHANGE EFFECT
  // ============================================================================
  useEffect(() => {
    if (!map.current || !mapLoaded || !urbanData) return;

    // Use smooth transition instead of instant switch
    smoothTransitionToYear(map.current, previousUrbanYear, urbanTimelineYear, 500);
    setPreviousUrbanYear(urbanTimelineYear);

  }, [urbanTimelineYear, mapLoaded, urbanData]);

  // Also update when urban data loads - set available years
  useEffect(() => {
    if (urbanData?.tile_urls) {
      const tiles = urbanData.tile_urls || (urbanData as any).tiles;
      const years = getAvailableYears(tiles);
      setUrbanAvailableYears(years);
      console.log('[Urban] Available years:', years);
    }
  }, [urbanData]);

  // Extract available years from water time series data
  useEffect(() => {
    if (waterData?.time_series && waterData.time_series.length > 0) {
      const years = waterData.time_series.map(point => point.year).sort((a, b) => a - b);
      setWaterAvailableYears(years);
      console.log('[Water] Available years:', years);
      // Set initial year to the latest year
      if (years.length > 0) {
        setWaterTimelineYear(years[years.length - 1]);
        setPreviousWaterYear(years[years.length - 1]);
      }
    }
  }, [waterData]);

  // ============================================================================
  // 💧 WATER LAYER EFFECT
  // ============================================================================
  useEffect(() => {
    if (!map.current || !mapLoaded || !waterData) return;

    // Toggle water layers based on state
    toggleWaterLayer(map.current, 'water-occurrence-layer', waterLayers.waterOccurrence);
    toggleWaterLayer(map.current, 'water-change-layer', waterLayers.waterChange);
    toggleWaterLayer(map.current, 'water-seasonality-layer', waterLayers.waterSeasonality);
    toggleWaterLayer(map.current, 'water-recurrence-layer', waterLayers.waterRecurrence);
    toggleWaterLayer(map.current, 'water-transitions-layer', waterLayers.waterTransitions);

  }, [waterLayers, mapLoaded, waterData]);

  // ============================================================================
  // 💧 WATER OPACITY EFFECT
  // ============================================================================
  useEffect(() => {
    if (!map.current || !mapLoaded || !waterData) return;

    const opacityKeys = Object.keys(waterOpacity) as (keyof WaterLayerOpacity)[];
    const layerMapping: Record<keyof WaterLayerOpacity, string> = {
      waterOccurrence: 'water-occurrence-layer',
      waterChange: 'water-change-layer',
      waterSeasonality: 'water-seasonality-layer',
      waterRecurrence: 'water-recurrence-layer',
      waterTransitions: 'water-transitions-layer'
    };

    opacityKeys.forEach((key) => {
      const layerId = layerMapping[key];
      const stateKey = key.replace('water', 'water') as keyof WaterLayerState;

      if (waterLayers[stateKey]) {
        updateWaterLayerOpacity(map.current!, layerId, waterOpacity[key]);
      }
    });

  }, [waterOpacity, waterLayers, mapLoaded, waterData]);

  // ============================================================================
  // 🌫️ AIR QUALITY LAYER EFFECT
  // ============================================================================
  useEffect(() => {
    if (!map.current || !mapLoaded || !airQualityData) return;

    // Toggle air quality layers based on state
    Object.entries(aqLayers).forEach(([pollutantKey, visible]) => {
      toggleAirQualityLayer(map.current!, pollutantKey, visible);
    });

  }, [aqLayers, mapLoaded, airQualityData]);

  // ============================================================================
  // 🌫️ AIR QUALITY OPACITY EFFECT
  // ============================================================================
  useEffect(() => {
    if (!map.current || !mapLoaded || !airQualityData) return;

    Object.entries(aqOpacity).forEach(([pollutantKey, opacity]) => {
      const stateKey = pollutantKey as keyof AQLayerState;
      if (aqLayers[stateKey]) {
        updateAirQualityOpacity(map.current!, pollutantKey, opacity);
      }
    });

  }, [aqOpacity, aqLayers, mapLoaded, airQualityData]);

  // ============================================================================
  // 💧 WATER TIMELINE YEAR CHANGE EFFECT
  // ============================================================================


  const flyToCountry = (countryCode: string) => {
    if (!map.current || !mapLoaded) return;

    const countryData = getCountryData(countryCode);
    if (!countryData) return;

    console.log('[Map] Flying to:', countryData.name);

    map.current.flyTo({
      center: countryData.center,
      zoom: countryData.zoom,
      duration: 2500,
      essential: true
    });

    setCurrentCountry(countryCode);
  };

  // ============================================================================
  // 🌊 FLOOD LAYER TOGGLE HANDLER
  // ============================================================================
  const handleToggleFloodLayer = (layer: keyof FloodLayerState) => {
    setFloodLayers(prev => ({
      ...prev,
      [layer]: !prev[layer]
    }));
  };

  // ============================================================================
  // 🌊 FLOOD OPACITY CHANGE HANDLER
  // ============================================================================
  const handleFloodOpacityChange = (layer: keyof FloodLayerOpacity, value: number) => {
    setFloodOpacity(prev => ({
      ...prev,
      [layer]: value
    }));
  };

  // ============================================================================
  // 🌊 CLEAR FLOOD DATA HELPER
  // ============================================================================
  const clearFloodData = () => {
    if (map.current) {
      removeFloodLayers(map.current);
    }
    setFloodData(null);
    setFloodLayers(DEFAULT_FLOOD_LAYERS);
    setFloodOpacity(DEFAULT_FLOOD_OPACITY);
  };

  // ============================================================================
  // 🛰️ CLEAR MPC DATA HELPER
  // ============================================================================
  const clearMPCData = () => {
    if (map.current) {
      removeMPCLayers(map.current);
    }
    setMpcData(null);
  };

  // ============================================================================
  // 🏙️ CLEAR URBAN DATA HELPER
  // ============================================================================
  const clearUrbanData = () => {
    if (map.current) {
      removeUrbanLayers(map.current);
    }
    setUrbanData(null);
    setUrbanLayers({
      urbanization_timeline: true,
      built_up: false,
      growth_layer: false
    });
    setUrbanTimelineYear(2020);
    setIsUrbanPlaying(false);
  };

  // ============================================================================
  // 💧 CLEAR WATER DATA HELPER
  // ============================================================================
  const clearWaterData = () => {
    if (map.current) {
      removeWaterLayers(map.current);
    }
    setWaterData(null);
    setWaterLayers(DEFAULT_WATER_LAYERS);
    setWaterOpacity(DEFAULT_WATER_OPACITY);
    setWaterTimelineYear(2021);
    setIsWaterPlaying(false);
  };


  // ============================================================================
  // 🌊 FLOOD SUB-REGION CLICK HANDLER
  // ============================================================================
  const handleFloodSubRegionClick = (regionName: string, regionType: string) => {
    console.log('[Dashboard] 🌊 Sub-region clicked:', regionName, regionType);

    const afterDate = floodData?.dates?.after?.start || '';
    const yearMonth = afterDate ? afterDate.substring(0, 7).replace('-', ' ') : 'August 2022';

    const newQuery = `Show floods in ${regionName} ${regionType} ${yearMonth}`;

    setChatInput(newQuery);
    setIsChatExpanded(true);
  };

  //  country boundary visualization
  const addCountryBoundary = async (countryCode: string) => {
    if (!map.current || !mapLoaded) return;

    try {
      console.log('[Boundary] Loading spotlight for:', countryCode);

      removeCountryBoundary();

      const boundaryData = await getCountryBoundary(countryCode);
      if (!boundaryData) return;

      if (!map.current.getSource(BOUNDARY_SOURCE_ID)) {
        map.current.addSource(BOUNDARY_SOURCE_ID, {
          type: 'geojson',
          data: boundaryData
        });
      } else {
        (map.current.getSource(BOUNDARY_SOURCE_ID) as maplibregl.GeoJSONSource).setData(boundaryData);
      }

      const GLOBAL_DARK_ID = 'global-darken';

      if (!map.current.getSource(GLOBAL_DARK_ID)) {
        const worldPolygon = {
          type: 'FeatureCollection' as const,
          features: [{
            type: 'Feature' as const,
            properties: {},
            geometry: {
              type: 'Polygon' as const,
              coordinates: [[
                [-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]
              ]]
            }
          }]
        };

        map.current.addSource(GLOBAL_DARK_ID, {
          type: 'geojson',
          data: worldPolygon
        });

        map.current.addLayer({
          id: GLOBAL_DARK_ID,
          type: 'fill',
          source: GLOBAL_DARK_ID,
          paint: {
            'fill-color': '#000000',
            'fill-opacity': 0.10
          }
        });
      }

      if (!map.current.getLayer(BOUNDARY_LINE_ID)) {
        map.current.addLayer({
          id: BOUNDARY_LINE_ID,
          type: 'line',
          source: BOUNDARY_SOURCE_ID,
          paint: {
            'line-color': '#FFFFFF',
            'line-width': 2.0,
            'line-opacity': 0.85,
            'line-blur': 0.3
          }
        });
      }

      const geometry = boundaryData.features[0]?.geometry;
      if (geometry?.coordinates) {
        const coordinates = flattenCoordinates(geometry.coordinates);

        if (coordinates.length > 0) {
          const bbox = coordinates.reduce(
            (bounds, coord) => [
              Math.min(bounds[0], coord[0]),
              Math.min(bounds[1], coord[1]),
              Math.max(bounds[2], coord[0]),
              Math.max(bounds[3], coord[1])
            ],
            [Infinity, Infinity, -Infinity, -Infinity]
          );

          map.current.fitBounds(
            [[bbox[0], bbox[1]], [bbox[2], bbox[3]]],
            {
              padding: { top: 80, bottom: 80, left: 80, right: 400 },
              duration: 2000,
              maxZoom: 7
            }
          );
        }
      }

      setShowBoundary(true);
      console.log('[Boundary] ✅ Clean border added');

    } catch (error) {
      console.error('[Boundary] Error:', error);
    }
  };

  //  Remove country boundary
  const removeCountryBoundary = () => {
    if (!map.current) return;

    const GLOBAL_DARK_ID = 'global-darken';

    [BOUNDARY_LINE_ID, BOUNDARY_FILL_ID, GLOBAL_DARK_ID].forEach(id => {
      if (map.current!.getLayer(id)) {
        map.current!.removeLayer(id);
      }
    });

    [BOUNDARY_SOURCE_ID, GLOBAL_DARK_ID].forEach(id => {
      if (map.current!.getSource(id)) {
        map.current!.removeSource(id);
      }
    });

    setShowBoundary(false);
  };

  // Toggle boundary visibility
  const toggleBoundaryVisibility = (visible: boolean) => {
    if (!map.current) return;

    const visibility = visible ? 'visible' : 'none';

    if (map.current.getLayer(BOUNDARY_FILL_ID)) {
      map.current.setLayoutProperty(BOUNDARY_FILL_ID, 'visibility', visibility);
    }

    if (map.current.getLayer(BOUNDARY_LINE_ID)) {
      map.current.setLayoutProperty(BOUNDARY_LINE_ID, 'visibility', visibility);
    }
  };

  // 🔥 Fire marker management
  const FIRE_SOURCE_ID = 'fires-source';
  const FIRE_LAYER_ID = 'fires-layer';

  const addFireMarkers = (fires: any[]) => {
    if (!map.current || !mapLoaded) return;

    console.log('[Fire] Adding fire markers:', fires.length);

    removeFireMarkers();

    const fireGeoJSON = {
      type: 'FeatureCollection' as const,
      features: fires.map(fire => ({
        type: 'Feature' as const,
        properties: {
          id: fire.id,
          confidence: fire.confidence,
          frp: fire.frp || 0,
          brightness: fire.brightness,
          satellite: fire.satellite,
          acq_time: fire.acq_time,
          daynight: fire.daynight
        },
        geometry: {
          type: 'Point' as const,
          coordinates: [fire.longitude, fire.latitude]
        }
      }))
    };

    map.current.addSource(FIRE_SOURCE_ID, {
      type: 'geojson',
      data: fireGeoJSON
    });

    map.current.addLayer({
      id: FIRE_LAYER_ID,
      type: 'circle',
      source: FIRE_SOURCE_ID,
      paint: {
        'circle-radius': [
          'interpolate',
          ['linear'],
          ['zoom'],
          0, 1.5,
          5, 2,
          8, 3,
          12, 4,
          16, 5
        ],
        'circle-color': [
          'match',
          ['get', 'confidence'],
          'h', '#FF0000',
          'n', '#FF6B00',
          'l', '#FFAA00',
          '#FF6B00'
        ],
        'circle-opacity': 0.8,
        'circle-stroke-width': 0.5,
        'circle-stroke-color': '#FFFFFF',
        'circle-stroke-opacity': 0.4
      }
    });

    map.current.on('click', FIRE_LAYER_ID, (e: any) => {
      if (!e.features || e.features.length === 0) return;

      const fire = e.features[0].properties;

      const popupHTML = `
    <div style="
      padding: 12px; 
      min-width: 220px; 
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      border-radius: 8px;
      border: 2px solid #f97316;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    ">
      <div style="
        font-weight: bold; 
        margin-bottom: 8px; 
        color: #fb923c;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 6px;
      ">
        <span style="font-size: 16px;">🔥</span> Fire Detection
      </div>
      <div style="
        font-size: 12px; 
        line-height: 1.7;
        color: #e2e8f0;
      ">
        <div style="margin-bottom: 4px;">
          <strong style="color: #cbd5e1;">Confidence:</strong> 
          <span style="color: ${fire.confidence === 'h' ? '#ef4444' : fire.confidence === 'n' ? '#f97316' : '#fbbf24'}; font-weight: 600;">
            ${fire.confidence === 'h' ? 'High' : fire.confidence === 'n' ? 'Nominal' : 'Low'}
          </span>
        </div>
        <div style="margin-bottom: 4px;">
          <strong style="color: #cbd5e1;">FRP:</strong> 
          <span style="color: #fb923c; font-weight: 600;">${fire.frp} MW</span>
        </div>
        <div style="margin-bottom: 4px;">
          <strong style="color: #cbd5e1;">Brightness:</strong> 
          <span style="color: #fbbf24; font-weight: 600;">${fire.brightness} K</span>
        </div>
        <div style="margin-bottom: 4px;">
          <strong style="color: #cbd5e1;">Time:</strong> 
          <span style="color: #e2e8f0;">${fire.acq_time} ${fire.daynight === 'D' ? '☀️ Day' : '🌙 Night'}</span>
        </div>
        <div>
          <strong style="color: #cbd5e1;">Satellite:</strong> 
          <span style="color: #94a3b8;">${fire.satellite}</span>
        </div>
      </div>
    </div>
  `;

      new maplibregl.Popup()
        .setLngLat(e.lngLat)
        .setHTML(popupHTML)
        .addTo(map.current!);
    });

    map.current.on('mouseenter', FIRE_LAYER_ID, () => {
      if (map.current) map.current.getCanvas().style.cursor = 'pointer';
    });

    map.current.on('mouseleave', FIRE_LAYER_ID, () => {
      if (map.current) map.current.getCanvas().style.cursor = '';
    });

    console.log('[Fire] ✅ Fire markers added (FIRMS style)');
  };

  const removeFireMarkers = () => {
    if (!map.current) return;

    const layersToRemove = [
      'fires-heatmap',
      'fires-clusters',
      'fires-cluster-count',
      FIRE_LAYER_ID
    ];

    layersToRemove.forEach(layerId => {
      if (map.current!.getLayer(layerId)) {
        map.current!.removeLayer(layerId);
      }
    });

    if (map.current.getSource(FIRE_SOURCE_ID)) {
      map.current.removeSource(FIRE_SOURCE_ID);
    }

    console.log('[Fire] Removed fire visualization layers');
  };


  // ============================================================================
  // 🎯 MAIN QUERY HANDLER - WITH FLOOD, FIRE, FOREST, MPC SUPPORT
  // ============================================================================
  const handleSendQuery = async () => {
    if (!chatInput.trim() || isLoadingQuery) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    setIsChatExpanded(true);
    setHasQueried(true);

    const detectedCountry = detectCountryFromQuery(userMessage);

    let queryToSend = userMessage;
    const driverKeywords = ['driver', 'cause', 'why', 'reason', 'show me drivers', 'what are the'];
    const hasDriverIntent = driverKeywords.some(kw => userMessage.toLowerCase().includes(kw));
    const hasCountryInQuery = /\b(brazil|indonesia|congo|pakistan|india|malaysia|peru|colombia|bolivia)\b/i.test(userMessage);

    if (hasDriverIntent && !hasCountryInQuery && currentCountry) {
      const countryName = getCountryName(currentCountry);
      queryToSend = `${userMessage} in ${countryName}`;
      console.log('[Query] Enhanced query with country:', queryToSend);
    }

    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoadingQuery(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/query/nl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: queryToSend,
          include_raw_data: true
        })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const apiResponse = await response.json();
      console.log('[Query] API Response:', apiResponse);
      console.log('[Query] Intent:', apiResponse.intent);

      // ========================================================================
      // 🌊 HANDLE FLOOD FOLLOW-UP INTENTS FIRST
      // ========================================================================

      const isFloodStatistics = apiResponse.intent === 'flood_statistics';
      const isFloodOptical = apiResponse.intent === 'flood_optical';

      if (isFloodStatistics) {
        console.log('[Dashboard] 📊 Flood statistics follow-up received');

        if (apiResponse.data && floodData) {
          setFloodData(prev => prev ? {
            ...prev,
            statistics: {
              ...prev.statistics,
              exposed_population: apiResponse.data.exposed_population || apiResponse.data.statistics?.exposed_population || 0,
              flooded_cropland_ha: apiResponse.data.flooded_cropland_ha || apiResponse.data.statistics?.flooded_cropland_ha || 0,
              flooded_urban_ha: apiResponse.data.flooded_urban_ha || apiResponse.data.statistics?.flooded_urban_ha || 0
            }
          } : null);

          console.log('[Dashboard] ✅ Flood statistics updated:', apiResponse.data);
        }

        const aiResponse = apiResponse.report || apiResponse.answer || 'Statistics loaded successfully';
        setChatMessages(prev => [...prev, { role: 'assistant', content: aiResponse }]);

        setIsLoadingQuery(false);
        return;
      }

      if (isFloodOptical) {
        console.log('[Dashboard] 🛰️ Flood optical follow-up received');

        if (apiResponse.data?.tiles && floodData) {
          const opticalTiles = apiResponse.data.tiles;

          const updatedTiles: FloodTiles = {
            ...floodData.tiles,
            optical_before: opticalTiles.optical_before,
            optical_after: opticalTiles.optical_after,
            false_color_after: opticalTiles.false_color_after,
            ndwi_after: opticalTiles.ndwi_after
          };

          setFloodData(prev => prev ? {
            ...prev,
            tiles: updatedTiles
          } : null);

          if (map.current) {
            addOpticalLayers(map.current, opticalTiles, floodLayers, floodOpacity);
          }

          setFloodLayers(prev => ({
            ...prev,
            opticalAfter: true,
            opticalBefore: false,
            falseColor: false,
            ndwi: false
          }));

          console.log('[Dashboard] ✅ Optical tiles added:', Object.keys(opticalTiles).filter(k => opticalTiles[k as keyof typeof opticalTiles]));
        }

        const aiResponse = apiResponse.report || apiResponse.answer || 'Optical imagery loaded successfully';
        setChatMessages(prev => [...prev, { role: 'assistant', content: aiResponse }]);

        setIsLoadingQuery(false);
        return;
      }

      // ========================================================================
      // STANDARD INTENT HANDLING
      // ========================================================================

      const responseCountry = apiResponse.data?.country || detectedCountry || currentCountry;

      const countryChanged = responseCountry !== currentCountry;
      console.log('[Query] Current country:', currentCountry, '| Response country:', responseCountry, '| Changed:', countryChanged);

      if (responseCountry && countryChanged) {
        flyToCountry(responseCountry);
        setCurrentCountry(responseCountry);
      }

      // ========================================
      // 🌊 FLOOD DETECTION (Initial Query)
      // ========================================
      const isFloodQuery = apiResponse.intent === 'query_floods';

      if (isFloodQuery && apiResponse.data?.show_flood) {
        console.log('[Dashboard] 🌊 Flood query detected, processing flood data...');

        if (map.current) {
          removeHansenLayers(map.current);
          if (hasDriverLayer(map.current)) {
            removeDriverLayer(map.current);
          }
          removeFireMarkers();
          removeMPCLayers(map.current);
        }

        setFireStats(null);
        setForestStats(null);
        setDriverBreakdown(null);
        setDriverLayerData(null);
        setMpcData(null);

        setFloodData(apiResponse.data);

        setFloodLayers(DEFAULT_FLOOD_LAYERS);
        setFloodOpacity(DEFAULT_FLOOD_OPACITY);

        if (map.current && apiResponse.data.tiles) {
          addFloodLayers(
            map.current,
            apiResponse.data.tiles,
            DEFAULT_FLOOD_LAYERS,
            DEFAULT_FLOOD_OPACITY
          );
        }

        if (map.current && apiResponse.data.center) {
          flyToFloodLocation(
            map.current,
            apiResponse.data.center,
            apiResponse.data.zoom || 9
          );
        }

        setAvailableLayers(['flood']);

        setVisibleLayers({
          baseline: false,
          loss: false,
          gain: false,
          drivers: false
        });

        console.log('[Dashboard] ✅ Flood data loaded successfully');

        const aiResponse = apiResponse.report || apiResponse.answer || 'Flood data loaded successfully';
        setChatMessages(prev => [...prev, { role: 'assistant', content: aiResponse }]);

        setIsLoadingQuery(false);
        return;
      }

      // ========================================================================
      // 🏙️ URBAN EXPANSION QUERY
      // ========================================================================
      const isUrbanQuery = apiResponse.intent === 'query_urban_expansion';

      if (isUrbanQuery && apiResponse.data) {
        console.log('[Dashboard] 🏙️ Urban expansion query detected...');

        // Clear other modules
        if (map.current) {
          removeHansenLayers(map.current);
          if (hasDriverLayer(map.current)) { removeDriverLayer(map.current); }
          removeFireMarkers();
          removeFloodLayers(map.current);
          removeMPCLayers(map.current);
          removeUrbanLayers(map.current); // Remove old urban layers before adding new ones
          removeWaterLayers(map.current);
        }
        setFireStats(null);
        setForestStats(null);
        setDriverBreakdown(null);
        setDriverLayerData(null);
        setFloodData(null);
        setMpcData(null);

        // Set Urban Data
        const urbanResponse = apiResponse.data as UrbanExpansionResponse;
        setUrbanData(urbanResponse);

        // Add Layers
        if (map.current) {
          addUrbanLayers(map.current, urbanResponse);

          // Fly to location
          // Fly to location - v5.3 FIX: Handle flat backend response
          const center = urbanResponse.location?.center || (urbanResponse as any).center;
          const zoom = (urbanResponse as any).zoom || 11;

          if (center) {
            map.current.flyTo({
              center: center,
              zoom: zoom,
              duration: 2000
            });
          }
        }

        setAvailableLayers(['urban']); // Custom marker

        // Response message
        const aiResponse = apiResponse.report || apiResponse.answer || `Urban analysis for ${urbanResponse.location.name} loaded.`;
        setChatMessages(prev => [...prev, { role: 'assistant', content: aiResponse }]);

        setIsLoadingQuery(false);
        return;
      }

      // ========================================================================
      // 💧 SURFACE WATER CHANGE QUERY
      // ========================================================================
      const isWaterQuery = apiResponse.intent === 'query_surface_water';

      if (isWaterQuery && apiResponse.data) {
        console.log('[Dashboard] 💧 Surface water query detected...');
        console.log('[Dashboard] Water response data:', apiResponse.data);

        // Clear other modules
        if (map.current) {
          removeHansenLayers(map.current);
          if (hasDriverLayer(map.current)) { removeDriverLayer(map.current); }
          removeFireMarkers();
          removeFloodLayers(map.current);
          removeMPCLayers(map.current);
          removeUrbanLayers(map.current);
        }
        setFireStats(null);
        setForestStats(null);
        setDriverBreakdown(null);
        setDriverLayerData(null);
        setFloodData(null);
        setMpcData(null);
        setUrbanData(null);

        // Set Water Data
        const waterResponse = apiResponse.data as SurfaceWaterResponse;
        setWaterData(waterResponse);

        // Add Layers
        if (map.current && waterResponse.tiles) {
          addWaterLayers(map.current, waterResponse, waterLayers, waterOpacity);

          // Fly to location - use flat structure
          const center = waterResponse.center;
          const zoom = waterResponse.zoom || 9;

          if (center) {
            flyToWaterLocation(map.current, center, zoom);
          }
        }

        setAvailableLayers(['water']);

        // Response message
        const locationName = waterResponse.location_name || 'water body';
        const aiResponse = apiResponse.report || apiResponse.answer ||
          `Surface water analysis for ${locationName} loaded.`;
        setChatMessages(prev => [...prev, { role: 'assistant', content: aiResponse }]);

        setIsLoadingQuery(false);
        return;
      }

      // ========================================================================
      // 🌫️ AIR QUALITY INDEX QUERY
      // ========================================================================
      const isAQIQuery = apiResponse.intent === 'query_air_quality';

      if (isAQIQuery && apiResponse.data) {
        console.log('[Dashboard] 🌫️ Air Quality query detected...');
        console.log('[Dashboard] AQI response data:', apiResponse.data);

        // Clear other modules
        if (map.current) {
          removeHansenLayers(map.current);
          if (hasDriverLayer(map.current)) { removeDriverLayer(map.current); }
          removeFireMarkers();
          removeFloodLayers(map.current);
          removeMPCLayers(map.current);
          removeUrbanLayers(map.current);
          removeWaterLayers(map.current);
        }
        setFireStats(null);
        setForestStats(null);
        setDriverBreakdown(null);
        setDriverLayerData(null);
        setFloodData(null);
        setMpcData(null);
        setUrbanData(null);
        setWaterData(null);

        // Set AQI Data
        const aqiResponse = apiResponse.data as AirQualityResponse;
        setAirQualityData(aqiResponse);

        // Add Layers
        if (map.current && aqiResponse.tiles) {
          addAirQualityLayers(map.current, aqiResponse, aqLayers, aqOpacity);

          // Fly to location
          const center = aqiResponse.map_config.center;
          const zoom = aqiResponse.map_config.zoom || 9;

          if (center) {
            map.current.flyTo({
              center: center,
              zoom: zoom,
              duration: 2000
            });
          }
        }

        setAvailableLayers(['airquality']);

        // Response message
        const locationName = aqiResponse.location.name || 'location';
        const aiResponse = apiResponse.report || apiResponse.answer ||
          `Air quality analysis for ${locationName} loaded. AQI Level: ${aqiResponse.air_quality_level?.level || 'N/A'}`;
        setChatMessages(prev => [...prev, { role: 'assistant', content: aiResponse }]);

        setIsLoadingQuery(false);
        return;
      }


      // ========================================================================
      // 🛰️ MPC SATELLITE IMAGERY QUERY
      // ========================================================================
      const isMPCQuery = apiResponse.intent === 'query_mpc_images';

      if (isMPCQuery && apiResponse.data?.show_mpc) {
        console.log('[Dashboard] 🛰️ MPC query detected, processing satellite imagery...');

        if (map.current) {
          removeHansenLayers(map.current);
          if (hasDriverLayer(map.current)) {
            removeDriverLayer(map.current);
          }
          removeFireMarkers();
          removeFloodLayers(map.current);
        }

        setFireStats(null);
        setForestStats(null);
        setDriverBreakdown(null);
        setDriverLayerData(null);
        setFloodData(null);

        setMpcData(apiResponse.data);

        if (map.current && apiResponse.data) {
          addMPCLayers(map.current, apiResponse.data);
        }

        if (map.current && apiResponse.data.center) {
          flyToMPCLocation(
            map.current,
            apiResponse.data.center,
            apiResponse.data.zoom || 10
          );
        }

        setAvailableLayers(['mpc']);

        setVisibleLayers({
          baseline: false,
          loss: false,
          gain: false,
          drivers: false
        });

        console.log('[Dashboard] ✅ MPC data loaded successfully');

        const aiResponse = apiResponse.report || apiResponse.answer || 'Satellite imagery search completed';
        setChatMessages(prev => [...prev, { role: 'assistant', content: aiResponse }]);

        setIsLoadingQuery(false);
        return;
      }

      // ========================================
      // 🔥 FIRE DETECTION
      // ========================================
      const isFireQuery = apiResponse.intent === 'query_fires_realtime' ||
        /\b(fire|fires|burning|wildfire|blaze)\b/i.test(userMessage);

      if (isFireQuery && responseCountry) {
        console.log('[Dashboard] 🔥 Fire query detected, fetching live fire data...');

        clearFloodData();
        clearMPCData();

        try {
          if (map.current) {
            removeHansenLayers(map.current);
            if (hasDriverLayer(map.current)) {
              removeDriverLayer(map.current);
            }
          }

          const fireData = await getLiveFireDetections(responseCountry, 2);

          console.log('[Dashboard] Fire data received:', fireData);

          if (fireData.success) {
            setFireStats(fireData.statistics);

            if (fireData.fires.length > 0) {
              addFireMarkers(fireData.fires);
            }

            setAvailableLayers(['fires']);

            setForestStats(null);
            setDriverBreakdown(null);
            setDriverLayerData(null);

            setVisibleLayers({
              baseline: false,
              loss: false,
              gain: false,
              drivers: false
            });

            await addCountryBoundary(responseCountry);

            console.log('[Dashboard] ✅ Fire data loaded successfully');

            const aiResponse = apiResponse.report || apiResponse.answer || 'Fire data loaded successfully';
            setChatMessages(prev => [...prev, { role: 'assistant', content: aiResponse }]);

            setIsLoadingQuery(false);
            return;
          }
        } catch (fireError) {
          console.error('[Dashboard] ❌ Fire data error:', fireError);
        }
      }

      // ========================================
      // FOREST/DRIVER LAYER LOADING
      // ========================================

      if (!isFloodQuery && !isMPCQuery && !isUrbanQuery && !isWaterQuery) {
        clearFloodData();
        clearMPCData();
        clearUrbanData();
        clearWaterData();
      }

      try {
        if (map.current && mapLoaded) {
          console.log('[Dashboard] Loading GEE tiles for:', responseCountry);
          console.log('[Dashboard] Intent:', apiResponse.intent);

          const isDriverQuery = apiResponse.intent === 'query_drivers';
          const isForestQuery = apiResponse.intent === 'query_forest';

          console.log('[Dashboard] Is driver query:', isDriverQuery);
          console.log('[Dashboard] Is forest query:', isForestQuery);
          console.log('[Dashboard] Country changed:', countryChanged);

          if (isForestQuery || isDriverQuery) {
            console.log('[Dashboard] Clearing fire data for forest/driver query');
            setFireStats(null);
            removeFireMarkers();
          }

          if (countryChanged) {
            console.log('[Dashboard] Country changed - removing all layers');

            removeHansenLayers(map.current);
            if (hasDriverLayer(map.current)) {
              removeDriverLayer(map.current);
            }

            setAvailableLayers([]);
            setDriverLayerData(null);
          }

          if (isForestQuery && (countryChanged || availableLayers.length === 0)) {
            console.log('[Dashboard] Loading Hansen tiles (baseline/loss/gain)...');

            try {
              const geeData = await getHansenForestTiles(responseCountry);

              const defaultVisibility: LayerVisibility = {
                baseline: true,
                loss: true,
                gain: false,
                drivers: false
              };

              const defaultOpacity = {
                baseline: 0.6,
                loss: 0.8,
                gain: 0.3,
                drivers: 0.7
              };

              removeHansenLayers(map.current);
              addHansenLayers(map.current, geeData, defaultVisibility, defaultOpacity);

              setAvailableLayers(['baseline', 'loss', 'gain']);
              setVisibleLayers(defaultVisibility);

              console.log('[Dashboard] ✅ Hansen layers loaded successfully');
              await addCountryBoundary(responseCountry);
            } catch (hansenError) {
              console.error('[Dashboard] ❌ Hansen layer error:', hansenError);
            }
          }

          if (isDriverQuery) {
            console.log('[Dashboard] 🎯 Driver query detected, loading driver layer...');

            try {
              const driverData = await getDriverTiles(responseCountry);

              console.log('[Dashboard] Driver data received:', driverData);

              if (driverData.success) {
                if (hasDriverLayer(map.current)) {
                  removeDriverLayer(map.current);
                }

                addDriverLayer(map.current, driverData, 0.7, true);

                setDriverLayerData(driverData);
                setVisibleLayers(prev => ({ ...prev, drivers: true }));
                setAvailableLayers(prev => {
                  const newLayers = [...new Set([...prev, 'drivers'])];
                  return newLayers;
                });

                console.log('[Dashboard] ✅ Driver layer loaded successfully');
              }
            } catch (driverError) {
              console.error('[Dashboard] ❌ Driver layer error:', driverError);
            }
          } else {
            if (hasDriverLayer(map.current)) {
              console.log('[Dashboard] Removing driver layer (forest query)');
              removeDriverLayer(map.current);
              setDriverLayerData(null);
              setVisibleLayers(prev => ({ ...prev, drivers: false }));
              setAvailableLayers(prev => prev.filter(layer => layer !== 'drivers'));
            }
          }
        }
      } catch (geeError) {
        console.error('[Dashboard] GEE tile error:', geeError);
      }

      if (apiResponse.data && apiResponse.intent !== 'query_drivers') {
        const data = apiResponse.data;

        const transformedYearlyData = (data.yearly_data || []).map((item: any) => ({
          year: item.year,
          loss: item.loss_ha || item.loss || 0
        }));

        setForestStats({
          totalLoss: data.summary?.total_loss_ha || 0,
          recentYear: data.summary?.recent_year || 2024,
          recentLoss: data.summary?.recent_loss_ha || 0,
          trend: data.trend_analysis?.trend || 'UNKNOWN',
          severity: data.trend_analysis?.severity || 'UNKNOWN',
          changePercent: data.trend_analysis?.change_percent || 0,
          peakYear: data.peak_loss_year?.year || 0,
          peakLoss: data.peak_loss_year?.loss_ha || 0,
          lowestYear: data.lowest_loss_year?.year || 0,
          lowestLoss: data.lowest_loss_year?.loss_ha || 0,
          yearlyData: transformedYearlyData,
          recentAvg: data.trend_analysis?.recent_avg_loss_ha || 0,
          earlyAvg: data.trend_analysis?.early_avg_loss_ha || 0,
          yearsAvailable: data.summary?.years_available || 0,
          dataRange: data.summary?.data_range || '',
          dataDescription: data.data_description || ''
        });

        if (data.driver_breakdown && Array.isArray(data.driver_breakdown)) {
          setDriverBreakdown(data.driver_breakdown);
        } else {
          setDriverBreakdown(null);
        }
      }

      const aiResponse = apiResponse.report || apiResponse.answer || 'Done';
      setChatMessages(prev => [...prev, { role: 'assistant', content: aiResponse }]);

    } catch (error: any) {
      console.error('[Query] Error:', error);

      let errorMessage = "Sorry, I encountered an error processing your query.";

      if (error.response && error.response.data && error.response.data.detail) {
        errorMessage = `Error: ${error.response.data.detail}`;
      } else if (error.message) {
        errorMessage = `Error: ${error.message}`;
      }

      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: errorMessage,
        isError: true
      }]);
    } finally {
      setIsLoadingQuery(false);
    }
  };

  return (
    <div className="relative h-screen w-screen bg-slate-950 text-gray-100 antialiased overflow-hidden">

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between p-4">
        {/* Left - GeoWise Box */}
        <div className="flex items-center gap-3 bg-slate-900/95 backdrop-blur-sm border border-cyan-500/30 rounded-lg px-4 py-2.5 shadow-2xl">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
            <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="text-base font-bold text-white tracking-tight leading-tight">GeoWise AI</span>
            <span className="text-[9px] text-cyan-400 font-medium tracking-widest uppercase leading-tight">Satellite Intelligence</span>
          </div>
        </div>

        {/* Right - DA Avatar Box */}
        <div className="h-11 w-11 rounded-lg bg-slate-900/95 backdrop-blur-sm border border-cyan-500/30 hover:border-cyan-400/60 flex items-center justify-center text-white font-bold text-xs cursor-pointer transition-all shadow-2xl">
          DA
        </div>
      </header>

      {/* Main content area */}
      <div className="relative z-40 flex h-screen">

        {/* Left sidebar - Layers */}
        {hasQueried && availableLayers.length > 0 && (
          <aside className="w-56 bg-slate-900/95 backdrop-blur-sm border-r border-slate-800 flex flex-col overflow-hidden pt-20">
            <div className="flex-1 overflow-y-auto p-4 space-y-4">

              <div>
                <h3 className="text-[11px] font-semibold text-gray-400 mb-2.5 uppercase tracking-wider">
                  Data Layers
                </h3>
                <div className="space-y-2">
                  {availableLayers.includes('baseline') && (
                    <label className={`flex items-center gap-2.5 p-2.5 rounded-md cursor-pointer transition-all border ${visibleLayers.baseline
                      ? 'bg-slate-800 border-slate-700'
                      : 'border-slate-800 hover:bg-slate-800/50 hover:border-slate-700'
                      }`}>
                      <input
                        type="checkbox"
                        checked={visibleLayers.baseline}
                        onChange={(e) => setVisibleLayers({ ...visibleLayers, baseline: e.target.checked })}
                        className="h-3.5 w-3.5 rounded accent-emerald-600 bg-slate-800 border-slate-700"
                      />
                      <div className="w-3.5 h-3.5 rounded-sm bg-gradient-to-br from-emerald-500 to-emerald-600"></div>
                      <div className="flex-1">
                        <div className="text-xs font-medium text-gray-200">Forest Density</div>
                        <div className="text-[10px] text-gray-500">Baseline 2000</div>
                      </div>
                    </label>
                  )}

                  {availableLayers.includes('loss') && (
                    <label className={`flex items-center gap-2.5 p-2.5 rounded-md cursor-pointer transition-all border ${visibleLayers.loss
                      ? 'bg-slate-800 border-slate-700'
                      : 'border-slate-800 hover:bg-slate-800/50 hover:border-slate-700'
                      }`}>
                      <input
                        type="checkbox"
                        checked={visibleLayers.loss}
                        onChange={(e) => setVisibleLayers({ ...visibleLayers, loss: e.target.checked })}
                        className="h-3.5 w-3.5 rounded accent-red-600 bg-slate-800 border-slate-700"
                      />
                      <div className="w-3.5 h-3.5 rounded-sm bg-gradient-to-br from-orange-500 to-red-600"></div>
                      <div className="flex-1">
                        <div className="text-xs font-medium text-gray-200">Tree Cover Loss</div>
                        <div className="text-[10px] text-gray-500">2001-2024</div>
                      </div>
                    </label>
                  )}

                  {availableLayers.includes('gain') && (
                    <label className={`flex items-center gap-2.5 p-2.5 rounded-md cursor-pointer transition-all border ${visibleLayers.gain
                      ? 'bg-slate-800 border-slate-700'
                      : 'border-slate-800 hover:bg-slate-800/50 hover:border-slate-700'
                      }`}>
                      <input
                        type="checkbox"
                        checked={visibleLayers.gain}
                        onChange={(e) => setVisibleLayers({ ...visibleLayers, gain: e.target.checked })}
                        className="h-3.5 w-3.5 rounded accent-blue-600 bg-slate-800 border-slate-700"
                      />
                      <div className="w-3.5 h-3.5 rounded-sm bg-gradient-to-br from-blue-500 to-blue-600"></div>
                      <div className="flex-1">
                        <div className="text-xs font-medium text-gray-200">Forest Gain</div>
                        <div className="text-[10px] text-gray-500">2000-2012</div>
                      </div>
                    </label>
                  )}

                  {availableLayers.includes('drivers') && (
                    <label className={`flex items-center gap-2.5 p-2.5 rounded-md cursor-pointer transition-all border ${visibleLayers.drivers
                      ? 'bg-slate-800 border-slate-700'
                      : 'border-slate-800 hover:bg-slate-800/50 hover:border-slate-700'
                      }`}>
                      <input
                        type="checkbox"
                        checked={visibleLayers.drivers}
                        onChange={(e) => setVisibleLayers({ ...visibleLayers, drivers: e.target.checked })}
                        className="h-3.5 w-3.5 rounded accent-orange-600 bg-slate-800 border-slate-700"
                      />
                      <div className="w-3.5 h-3.5 rounded-sm bg-gradient-to-br from-orange-400 to-red-600"></div>
                      <div className="flex-1">
                        <div className="text-xs font-medium text-gray-200">Loss Drivers</div>
                        <div className="text-[10px] text-gray-500">2001-2024</div>
                      </div>
                    </label>
                  )}

                  {availableLayers.includes('fires') && (
                    <label className={`flex items-center gap-2.5 p-2.5 rounded-md cursor-pointer transition-all border bg-slate-800 border-slate-700`}>
                      <input
                        type="checkbox"
                        defaultChecked={true}
                        onChange={(e) => {
                          if (map.current) {
                            const visibility = e.target.checked ? 'visible' : 'none';
                            if (map.current.getLayer(FIRE_LAYER_ID)) {
                              map.current.setLayoutProperty(FIRE_LAYER_ID, 'visibility', visibility);
                            }
                          }
                        }}
                        className="h-3.5 w-3.5 rounded accent-orange-600 bg-slate-800 border-slate-700"
                      />
                      <div className="w-3.5 h-3.5 rounded-full bg-gradient-to-br from-orange-500 to-red-600"></div>
                      <div className="flex-1">
                        <div className="text-xs font-medium text-gray-200">Active Fires</div>
                        <div className="text-[10px] text-gray-500">Real-time detection</div>
                      </div>
                    </label>
                  )}

                  {/* MPC LAYER CONTROL */}
                  {availableLayers.includes('mpc') && (
                    <label className={`flex items-center gap-2.5 p-2.5 rounded-md cursor-pointer transition-all border bg-slate-800 border-slate-700`}>
                      <input
                        type="checkbox"
                        defaultChecked={true}
                        className="h-3.5 w-3.5 rounded accent-blue-600 bg-slate-800 border-slate-700"
                      />
                      <div className="w-3.5 h-3.5 rounded-sm bg-gradient-to-br from-blue-500 to-cyan-600"></div>
                      <div className="flex-1">
                        <div className="text-xs font-medium text-gray-200">Satellite Imagery</div>
                        <div className="text-[10px] text-gray-500">Search Results</div>
                      </div>
                    </label>
                  )}

                  {/* FLOOD LAYER CONTROLS */}
                  {availableLayers.includes('flood') && floodData?.tiles && (
                    <div className="mt-4 pt-4 border-t border-slate-700">
                      <FloodLayerControls
                        tiles={floodData.tiles}
                        layers={floodLayers}
                        opacity={floodOpacity}
                        onToggleLayer={handleToggleFloodLayer}
                        onOpacityChange={handleFloodOpacityChange}
                      />
                    </div>
                  )}

                  {showBoundary && (
                    <label className={`flex items-center gap-2.5 p-2.5 rounded-md cursor-pointer transition-all border bg-slate-800 border-slate-700`}>
                      <input
                        type="checkbox"
                        defaultChecked={true}
                        onChange={(e) => toggleBoundaryVisibility(e.target.checked)}
                        className="h-3.5 w-3.5 rounded accent-cyan-600 bg-slate-800 border-slate-700"
                      />
                      <div className="w-3.5 h-3.5 rounded-sm bg-gradient-to-br from-cyan-400 to-cyan-600"></div>
                      <div className="flex-1">
                        <div className="text-xs font-medium text-gray-200">Country Boundary</div>
                        <div className="text-[10px] text-gray-500">{getCountryName(currentCountry)}</div>
                      </div>
                    </label>
                  )}
                </div>
              </div>

              {availableLayers.includes('drivers') && visibleLayers.drivers && driverLayerData && (
                <div className="mt-4 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                  <h3 className="text-xs font-semibold mb-2.5 text-gray-200">Deforestation Drivers</h3>
                  <div className="space-y-1.5">
                    {Object.entries(driverLayerData.driver_categories).map(([id, category]) => (
                      <div key={id} className="flex items-start gap-1.5 text-[10px]">
                        <div
                          className="w-3 h-3 rounded flex-shrink-0 mt-0.5"
                          style={{ backgroundColor: category.color }}
                        />
                        <div className="flex-1">
                          <div className="text-gray-200 font-medium leading-tight">{category.name}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-2.5 pt-2.5 border-t border-slate-700">
                    <p className="text-[9px] text-gray-500">
                      Source: {driverLayerData.dataset_info.source}
                    </p>
                  </div>
                </div>

              )}

              {/* URBAN LAYER CONTROLS - v5.3 FIX: Moved to sidebar */}
              {availableLayers.includes('urban') && urbanData && (
                <div className="mt-4 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                  <h3 className="text-xs font-semibold mb-2.5 text-gray-200">Urban Expansion Layers</h3>
                  <div className="space-y-2">
                    {/* Timeline */}
                    <label className={`flex items-center gap-2.5 p-2 rounded-md cursor-pointer transition-all border ${urbanLayers.urbanization_timeline
                      ? 'bg-slate-800 border-slate-700'
                      : 'border-transparent hover:bg-slate-800/50'
                      }`}>
                      <input
                        type="checkbox"
                        checked={urbanLayers.urbanization_timeline}
                        onChange={(e) => {
                          const visible = e.target.checked;
                          setUrbanLayers(prev => ({ ...prev, urbanization_timeline: visible }));
                          if (map.current) toggleUrbanLayer(map.current, 'urban-timeline-layer', visible);
                        }}
                        className="h-3.5 w-3.5 rounded accent-purple-500 bg-slate-800 border-slate-700"
                      />
                      <div className="w-3.5 h-3.5 rounded-sm bg-gradient-to-br from-purple-500 to-blue-500"></div>
                      <div className="flex-1">
                        <div className="text-xs font-medium text-gray-200">Urbanization Timeline</div>
                        <div className="text-[10px] text-gray-500">Growth over time</div>
                      </div>
                    </label>

                    {/* Built-up */}
                    <label className={`flex items-center gap-2.5 p-2 rounded-md cursor-pointer transition-all border ${urbanLayers.built_up
                      ? 'bg-slate-800 border-slate-700'
                      : 'border-transparent hover:bg-slate-800/50'
                      }`}>
                      <input
                        type="checkbox"
                        checked={urbanLayers.built_up}
                        onChange={(e) => {
                          const visible = e.target.checked;
                          setUrbanLayers(prev => ({ ...prev, built_up: visible }));
                          if (map.current) toggleUrbanLayer(map.current, 'urban-built-layer', visible);
                        }}
                        className="h-3.5 w-3.5 rounded accent-pink-500 bg-slate-800 border-slate-700"
                      />
                      <div className="w-3.5 h-3.5 rounded-sm bg-pink-500/50"></div>
                      <div className="flex-1">
                        <div className="text-xs font-medium text-gray-200">Built-up Surface</div>
                        <div className="text-[10px] text-gray-500">Latest Extent</div>
                      </div>
                    </label>

                    {/* Growth Layer */}
                    <label className={`flex items-center gap-2.5 p-2 rounded-md cursor-pointer transition-all border ${urbanLayers.growth_layer
                      ? 'bg-slate-800 border-slate-700'
                      : 'border-transparent hover:bg-slate-800/50'
                      }`}>
                      <input
                        type="checkbox"
                        checked={urbanLayers.growth_layer}
                        onChange={(e) => {
                          const visible = e.target.checked;
                          setUrbanLayers(prev => ({ ...prev, growth_layer: visible }));
                          if (map.current) toggleUrbanLayer(map.current, 'urban-growth-layer', visible);
                        }}
                        className="h-3.5 w-3.5 rounded accent-green-500 bg-slate-800 border-slate-700"
                      />
                      <div className="w-3.5 h-3.5 rounded-sm bg-green-500/50"></div>
                      <div className="flex-1">
                        <div className="text-xs font-medium text-gray-200">New Urban Areas</div>
                        <div className="text-[10px] text-gray-500">Growth Zones</div>
                      </div>
                    </label>
                  </div>
                </div>
              )}

              {/* Water Layer Controls */}
              {availableLayers.includes('water') && waterData && (
                <div className="mt-4 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                  <WaterLayerControl
                    layers={waterLayers}
                    opacity={waterOpacity}
                    onLayerToggle={(layer) => {
                      setWaterLayers(prev => ({ ...prev, [layer]: !prev[layer] }));
                    }}
                    onOpacityChange={(layer, value) => {
                      setWaterOpacity(prev => ({ ...prev, [layer]: value }));
                    }}
                  />
                </div>
              )}

              {/* Air Quality Layer Controls */}
              {availableLayers.includes('airquality') && airQualityData && (
                <div className="mt-4 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                  <AirQualityLayerControl
                    layers={aqLayers}
                    opacity={aqOpacity}
                    onLayerToggle={(pollutant) => {
                      setAqLayers(prev => ({ ...prev, [pollutant]: !prev[pollutant] }));
                    }}
                    onOpacityChange={(pollutant, value) => {
                      setAqOpacity(prev => ({ ...prev, [pollutant]: value }));
                    }}
                  />
                </div>
              )}
            </div>
          </aside>
        )}

        {/* Map container */}
        <div className="flex-1 relative bg-slate-950">
          <div
            ref={mapContainer}
            className="absolute inset-0 w-full h-full"
          />

          {!mapLoaded && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-950/90">
              <div className="text-center">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500 mx-auto mb-3"></div>
                <p className="text-sm text-gray-400">Loading map...</p>
              </div>
            </div>
          )}

          {/* Welcome Overlay - Earth Observation Analysis */}
          {!hasQueried && mapLoaded && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-950/20 backdrop-blur-sm pointer-events-none z-20">
              <div className="text-center max-w-2xl px-8 pointer-events-auto -mt-20">
                {/* Animated Earth Icon */}
                <div className="mb-6 flex justify-center">
                  <div className="relative">
                    <div className="absolute inset-0 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full blur-2xl opacity-30 animate-pulse"></div>
                    <div className="relative text-6xl filter drop-shadow-2xl">🌍</div>
                  </div>
                </div>

                {/* Main Title with animated gradient */}
                <h1 className="text-4xl md:text-5xl font-black mb-4 bg-gradient-to-r from-white via-cyan-200 to-blue-300 bg-clip-text text-transparent tracking-tight animate-pulse">
                  See Earth's Story Unfold
                </h1>
                <p className="text-gray-300 text-base mb-10 max-w-2xl mx-auto leading-relaxed font-light">
                  Discover how our planet is changing through powerful satellite intelligence and AI-driven insights
                </p>

                {/* Enhanced Capabilities Grid */}
                <div className="flex items-center justify-center gap-6 mb-10">
                  <div className="group relative cursor-pointer">
                    <div className="absolute inset-0 bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl blur-xl opacity-20 group-hover:opacity-60 transition-all duration-500"></div>
                    <div className="relative bg-gradient-to-br from-purple-500/10 to-pink-500/10 border-2 border-purple-400/20 hover:border-purple-400/60 rounded-2xl p-4 backdrop-blur-md transition-all duration-300 transform group-hover:scale-110">
                      <div className="text-4xl mb-1">🏙️</div>
                      <p className="text-[10px] text-purple-300 font-semibold tracking-wide">URBAN</p>
                    </div>
                  </div>
                  <div className="group relative cursor-pointer">
                    <div className="absolute inset-0 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-2xl blur-xl opacity-20 group-hover:opacity-60 transition-all duration-500"></div>
                    <div className="relative bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border-2 border-blue-400/20 hover:border-blue-400/60 rounded-2xl p-4 backdrop-blur-md transition-all duration-300 transform group-hover:scale-110">
                      <div className="text-4xl mb-1">💧</div>
                      <p className="text-[10px] text-blue-300 font-semibold tracking-wide">WATER</p>
                    </div>
                  </div>
                  <div className="group relative cursor-pointer">
                    <div className="absolute inset-0 bg-gradient-to-br from-green-500 to-emerald-500 rounded-2xl blur-xl opacity-20 group-hover:opacity-60 transition-all duration-500"></div>
                    <div className="relative bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-2 border-green-400/20 hover:border-green-400/60 rounded-2xl p-4 backdrop-blur-md transition-all duration-300 transform group-hover:scale-110">
                      <div className="text-4xl mb-1">🌳</div>
                      <p className="text-[10px] text-green-300 font-semibold tracking-wide">FOREST</p>
                    </div>
                  </div>
                  <div className="group relative cursor-pointer">
                    <div className="absolute inset-0 bg-gradient-to-br from-orange-500 to-red-500 rounded-2xl blur-xl opacity-20 group-hover:opacity-60 transition-all duration-500"></div>
                    <div className="relative bg-gradient-to-br from-orange-500/10 to-red-500/10 border-2 border-orange-400/20 hover:border-orange-400/60 rounded-2xl p-4 backdrop-blur-md transition-all duration-300 transform group-hover:scale-110">
                      <div className="text-4xl mb-1">🔥</div>
                      <p className="text-[10px] text-orange-300 font-semibold tracking-wide">FIRE</p>
                    </div>
                  </div>
                </div>

                {/* Enhanced Call to Action */}
                <div className="flex items-center justify-center gap-4">
                  <div className="h-px flex-1 max-w-[120px] bg-gradient-to-r from-transparent via-cyan-500/30 to-cyan-500/60"></div>
                  <div className="flex items-center gap-2 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-500/30 rounded-full px-4 py-2 backdrop-blur-sm">
                    <svg className="h-4 w-4 animate-bounce text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                    </svg>
                    <p className="text-xs text-cyan-300 font-semibold tracking-wide">START ANALYZING</p>
                  </div>
                  <div className="h-px flex-1 max-w-[120px] bg-gradient-to-l from-transparent via-cyan-500/30 to-cyan-500/60"></div>
                </div>
              </div>
            </div>
          )}

          {/* Map legend */}
          {hasQueried && availableLayers.length > 0 && (
            <div className="absolute top-4 left-4 bg-slate-900/95 backdrop-blur-sm rounded-lg shadow-lg border border-slate-800 p-3 max-w-xs z-10">
              <h4 className="text-[11px] font-semibold text-gray-400 mb-2 uppercase tracking-wide">Legend</h4>
              <div className="space-y-2">
                {availableLayers.includes('baseline') && visibleLayers.baseline && (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-2.5 rounded-sm bg-gradient-to-r from-emerald-500 to-emerald-600"></div>
                    <span className="text-[10px] font-medium text-gray-300">Forest Density (2000)</span>
                  </div>
                )}

                {availableLayers.includes('loss') && visibleLayers.loss && (
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-2.5 rounded-sm bg-gradient-to-r from-orange-500 to-red-600"></div>
                      <span className="text-[10px] font-medium text-gray-300">Tree Cover Loss</span>
                    </div>
                  </div>
                )}

                {availableLayers.includes('gain') && visibleLayers.gain && (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-2.5 rounded-sm bg-blue-500"></div>
                    <span className="text-[10px] font-medium text-gray-300">Forest Gain (2000-2012)</span>
                  </div>
                )}

                {availableLayers.includes('drivers') && visibleLayers.drivers && (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-2.5 rounded-sm bg-gradient-to-r from-orange-400 to-red-600"></div>
                    <span className="text-[10px] font-medium text-gray-300">Deforestation Drivers</span>
                  </div>
                )}

                {availableLayers.includes('fires') && (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-2.5 rounded-full bg-gradient-to-r from-orange-500 to-red-600"></div>
                    <span className="text-[10px] font-medium text-gray-300">Active Fires (NASA FIRMS)</span>
                  </div>
                )}

                {/* MPC LEGEND */}
                {availableLayers.includes('mpc') && mpcData && (
                  <div className="space-y-1.5 pt-2 border-t border-slate-700">
                    <div className="text-[10px] font-semibold text-gray-400 uppercase">Satellite Imagery</div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-2.5 rounded-sm border-2 border-dashed" style={{
                        borderColor: getCollectionColor(mpcData.collection)
                      }}></div>
                      <span className="text-[10px] font-medium text-gray-300">Search Area</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded-full flex items-center justify-center text-white text-[8px] font-bold" style={{
                        backgroundColor: getCollectionColor(mpcData.collection)
                      }}>
                        {mpcData.images_found || 0}
                      </div>
                      <span className="text-[10px] font-medium text-gray-300">Available Images</span>
                    </div>
                  </div>
                )}

                {availableLayers.includes('flood') && (
                  <div className="space-y-1.5 pt-2 border-t border-slate-700">
                    <div className="text-[10px] font-semibold text-gray-400 uppercase">Flood Detection</div>
                    {floodLayers.floodExtent && (
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-2.5 rounded-sm bg-red-500"></div>
                        <span className="text-[10px] font-medium text-gray-300">Flood Extent</span>
                      </div>
                    )}
                    {floodLayers.changeDetection && (
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-2.5 rounded-sm bg-gradient-to-r from-blue-500 to-red-500"></div>
                        <span className="text-[10px] font-medium text-gray-300">SAR Change</span>
                      </div>
                    )}
                    {floodLayers.permanentWater && (
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-2.5 rounded-sm bg-cyan-400"></div>
                        <span className="text-[10px] font-medium text-gray-300">Permanent Water</span>
                      </div>
                    )}
                    {floodLayers.opticalAfter && (
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-2.5 rounded-sm bg-green-500"></div>
                        <span className="text-[10px] font-medium text-gray-300">Optical Imagery</span>
                      </div>
                    )}
                  </div>
                )}

                {/* WATER LEGEND */}
                {availableLayers.includes('water') && waterData && (
                  <div className="space-y-1.5 pt-2 border-t border-slate-700">
                    <div className="text-[10px] font-semibold text-gray-400 uppercase">Surface Water</div>
                    {waterLayers.waterOccurrence && (
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-2.5 rounded-sm bg-blue-500"></div>
                        <span className="text-[10px] font-medium text-gray-300">Water Occurrence</span>
                      </div>
                    )}
                    {waterLayers.waterChange && (
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-2.5 rounded-sm bg-gradient-to-r from-red-500 to-green-500"></div>
                        <span className="text-[10px] font-medium text-gray-300">Water Change</span>
                      </div>
                    )}
                    {waterLayers.waterSeasonality && (
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-2.5 rounded-sm bg-cyan-400"></div>
                        <span className="text-[10px] font-medium text-gray-300">Seasonality</span>
                      </div>
                    )}
                    {waterLayers.waterRecurrence && (
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-2.5 rounded-sm bg-blue-300"></div>
                        <span className="text-[10px] font-medium text-gray-300">Recurrence</span>
                      </div>
                    )}
                    {waterLayers.waterTransitions && (
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-2.5 rounded-sm bg-gradient-to-r from-blue-600 to-cyan-400"></div>
                        <span className="text-[10px] font-medium text-gray-300">Transitions</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* URBAN TIMELINE SLIDER */}
          {urbanData && (
            <UrbanTimelineSlider
              years={urbanAvailableYears}
              currentYear={urbanTimelineYear}
              onYearChange={(year, prevYear) => {
                if (prevYear) setPreviousUrbanYear(prevYear);
                setUrbanTimelineYear(year);
              }}
              isPlaying={isUrbanPlaying}
              onPlayToggle={setIsUrbanPlaying}
              onShowGif={() => setShowUrbanGif(true)}
            />
          )}

        </div>

        {/* Right sidebar - Stats */}
        {hasQueried && showStatsPanel && (
          <>
            {mpcData ? (
              <MPCStatsPanel
                data={mpcData}
                loading={isLoadingQuery}
              />
            ) : floodData ? (
              <FloodStatsPanel
                data={floodData}
                locationName={floodData.location_name || 'Unknown Location'}
                onSubRegionClick={handleFloodSubRegionClick}
              />
            ) : fireStats ? (
              <FireStatsPanel
                statistics={fireStats}
                countryName={getCountryName(currentCountry)}
              />
            ) : urbanData ? (
              <UrbanStatsPanel
                data={urbanData}
                isLoading={isLoadingQuery}
              />
            ) : waterData ? (
              <WaterStatsPanel
                data={waterData}
                isLoading={isLoadingQuery}
              />
            ) : airQualityData ? (
              <AirQualityStatsPanel
                data={airQualityData}
              />
            ) : (

              forestStats && (
                <aside className="w-[360px] bg-slate-900/95 backdrop-blur-sm border-l border-slate-800 overflow-y-auto">
                  {/* ... EXISTING FOREST STATS PANEL CODE ... */}
                  {/* (Keep all your existing forest stats panel JSX exactly as is) */}
                  <div className="p-4 space-y-3.5">

                    <div className="pb-2.5 border-b border-slate-800">
                      <div className="flex items-start justify-between">
                        <div>
                          <h2 className="text-xl font-bold text-gray-100">{getCountryName(currentCountry)}</h2>
                          <p className="text-[11px] text-gray-500 mt-1">
                            Tree Cover Loss Analysis • {forestStats.dataRange}
                          </p>
                        </div>
                        <span className="text-[10px] px-2 py-1 bg-emerald-950/50 text-emerald-400 rounded font-medium border border-emerald-900/50">GFW</span>
                      </div>
                    </div>

                    {forestStats.yearlyData && forestStats.yearlyData.length > 0 && (
                      <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
                        <p className="text-xs text-gray-300 leading-relaxed">
                          From <strong className="text-gray-100">{forestStats.yearlyData[0]?.year || 2001}</strong> to <strong className="text-gray-100">{forestStats.recentYear}</strong>,{' '}
                          {getCountryName(currentCountry)} lost{' '}
                          <strong className="text-red-400">{(forestStats.totalLoss / 1000000).toFixed(1)} Mha</strong> of tree cover.
                        </p>
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-2.5">
                      <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
                        <div className="text-[10px] text-gray-500 mb-1 uppercase font-semibold tracking-wide">Total Loss</div>
                        <div className="text-2xl font-bold text-red-400">
                          {(forestStats.totalLoss / 1000000).toFixed(1)} Mha
                        </div>
                        <div className="text-[10px] text-gray-600 mt-0.5">{forestStats.dataRange}</div>
                      </div>

                      <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800">
                        <div className="text-[10px] text-gray-500 mb-1 uppercase font-semibold tracking-wide">{forestStats.recentYear} Loss</div>
                        <div className="text-2xl font-bold text-orange-400">
                          {(forestStats.recentLoss / 1000).toFixed(0)} kha
                        </div>
                        <div className="text-[10px] text-gray-600 mt-0.5">recent year</div>
                      </div>
                    </div>

                    {forestStats.yearlyData && forestStats.yearlyData.length > 0 && (
                      <div className="bg-slate-800/50 rounded-lg border border-slate-800 overflow-hidden">
                        <div className="p-3 border-b border-slate-800">
                          <h3 className="text-xs font-bold text-gray-100">RECENT YEARS (LAST 10)</h3>
                        </div>

                        <div className="p-3">
                          {(() => {
                            const last10 = forestStats.yearlyData.slice(-10);
                            const maxLoss = Math.max(...last10.map(d => d.loss));
                            const minLoss = Math.min(...last10.map(d => d.loss));

                            const getRelativeHeight = (value: number) => {
                              if (maxLoss === minLoss) return 100;
                              const normalized = (value - minLoss) / (maxLoss - minLoss);
                              return 20 + (normalized * 80);
                            };

                            return (
                              <>
                                <div className="h-40 flex items-end justify-between gap-0.5 bg-slate-900/50 p-2 rounded relative">
                                  {last10.map((yearData, idx) => {
                                    const heightPercent = getRelativeHeight(yearData.loss);
                                    const heightPx = (heightPercent / 100) * 144;

                                    return (
                                      <div key={idx} className="flex-1 flex flex-col items-center justify-end group relative">
                                        <div
                                          className="w-full bg-gradient-to-t from-red-600 via-red-500 to-orange-400 hover:from-red-700 hover:via-red-600 hover:to-orange-500 transition-all cursor-pointer rounded-t"
                                          style={{
                                            height: `${heightPx}px`,
                                            minHeight: '16px'
                                          }}
                                        >
                                          <div className="absolute -top-14 left-1/2 -translate-x-1/2 bg-slate-950 text-gray-100 text-[10px] px-2 py-1 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20 border border-slate-800">
                                            <div className="font-semibold">{yearData.year}</div>
                                            <div className="text-gray-400">{(yearData.loss / 1000).toFixed(1)} kha</div>
                                          </div>
                                        </div>
                                        <span className="text-[9px] text-gray-500 mt-1">{yearData.year}</span>
                                      </div>
                                    );
                                  })}
                                </div>

                                <div className="flex justify-between mt-2 text-[9px] text-gray-600">
                                  <span>Min: {(minLoss / 1000).toFixed(0)}k ha</span>
                                  <span>Max: {(maxLoss / 1000).toFixed(0)}k ha</span>
                                </div>
                              </>
                            );
                          })()}
                        </div>
                      </div>
                    )}

                    <div className="bg-slate-800/50 rounded-lg border border-slate-800 p-3">
                      <h3 className="text-xs font-bold text-gray-100 mb-2">TREND ANALYSIS</h3>
                      <div className="grid grid-cols-2 gap-3 text-[11px]">
                        <div>
                          <div className="text-gray-500 mb-0.5">Trend</div>
                          <div className={`font-bold text-base ${forestStats.trend === 'INCREASING' ? 'text-red-400' :
                            forestStats.trend === 'DECREASING' ? 'text-emerald-400' : 'text-amber-400'
                            }`}>
                            {forestStats.trend}
                          </div>
                        </div>
                        <div>
                          <div className="text-gray-500 mb-0.5">Severity</div>
                          <div className="font-bold text-base text-gray-200">{forestStats.severity}</div>
                        </div>
                        <div>
                          <div className="text-gray-500 mb-0.5">Change Rate</div>
                          <div className="font-bold text-base text-gray-200">{forestStats.changePercent.toFixed(1)}%</div>
                        </div>
                        <div>
                          <div className="text-gray-500 mb-0.5">Period</div>
                          <div className="font-bold text-base text-gray-200">{forestStats.yearsAvailable} years</div>
                        </div>
                      </div>
                    </div>

                    {driverBreakdown && driverBreakdown.length > 0 && (
                      <div className="bg-slate-800/50 rounded-lg border border-slate-800 overflow-hidden">
                        <div className="p-3 border-b border-slate-800">
                          <h3 className="text-xs font-bold text-gray-100">DRIVERS OF DEFORESTATION</h3>
                          <p className="text-[10px] text-gray-500 mt-0.5">
                            Causes of forest loss in {forestStats.recentYear}
                          </p>
                        </div>

                        <div className="p-3">
                          {(() => {
                            const colors = [
                              '#EF4444', '#F97316', '#F59E0B', '#10B981',
                              '#3B82F6', '#8B5CF6', '#EC4899', '#6B7280'
                            ];

                            let cumulativePercent = 0;

                            return (
                              <div className="space-y-3">
                                <div className="relative w-40 h-40 mx-auto">
                                  <svg viewBox="0 0 100 100" className="transform -rotate-90">
                                    {driverBreakdown.map((driver, idx) => {
                                      const percent = driver.percentage;
                                      const startPercent = cumulativePercent;
                                      cumulativePercent += percent;

                                      const startAngle = (startPercent / 100) * 360;
                                      const endAngle = (cumulativePercent / 100) * 360;

                                      const x1 = 50 + 40 * Math.cos((Math.PI * startAngle) / 180);
                                      const y1 = 50 + 40 * Math.sin((Math.PI * startAngle) / 180);
                                      const x2 = 50 + 40 * Math.cos((Math.PI * endAngle) / 180);
                                      const y2 = 50 + 40 * Math.sin((Math.PI * endAngle) / 180);

                                      const largeArc = percent > 50 ? 1 : 0;

                                      return (
                                        <path
                                          key={idx}
                                          d={`M 50 50 L ${x1} ${y1} A 40 40 0 ${largeArc} 1 ${x2} ${y2} Z`}
                                          fill={colors[idx % colors.length]}
                                          className="hover:opacity-80 transition-opacity cursor-pointer"
                                        />
                                      );
                                    })}
                                    <circle cx="50" cy="50" r="25" fill="#0f172a" />
                                  </svg>
                                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                                    <div className="text-xl font-bold text-gray-100">
                                      {driverBreakdown.reduce((sum, d) => sum + d.percentage, 0).toFixed(0)}%
                                    </div>
                                    <div className="text-[9px] text-gray-500">Total Loss</div>
                                  </div>
                                </div>

                                <div className="space-y-1.5">
                                  {driverBreakdown.map((driver, idx) => (
                                    <div key={idx} className="flex items-center justify-between text-[11px]">
                                      <div className="flex items-center gap-1.5 flex-1">
                                        <div
                                          className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                                          style={{ backgroundColor: colors[idx % colors.length] }}
                                        ></div>
                                        <span className="text-gray-300 truncate">
                                          {driver.driver_category}
                                        </span>
                                      </div>
                                      <div className="flex items-center gap-1.5 ml-2">
                                        <span className="font-semibold text-gray-100">{driver.percentage.toFixed(1)}%</span>
                                        <span className="text-gray-600 text-[10px]">
                                          ({(driver.loss_ha / 1000).toFixed(1)}k ha)
                                        </span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            );
                          })()}
                        </div>
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-2.5">
                      <div className="bg-red-950/20 rounded-lg p-3 border border-red-900/30">
                        <div className="text-[10px] text-gray-500 mb-0.5 uppercase font-semibold">Peak Year</div>
                        <div className="text-xl font-bold text-red-400">{forestStats.peakYear}</div>
                        <div className="text-[10px] text-gray-600 mt-0.5">{(forestStats.peakLoss / 1000).toFixed(0)} kha</div>
                      </div>

                      <div className="bg-emerald-950/20 rounded-lg p-3 border border-emerald-900/30">
                        <div className="text-[10px] text-gray-500 mb-0.5 uppercase font-semibold">Lowest Year</div>
                        <div className="text-xl font-bold text-emerald-400">{forestStats.lowestYear}</div>
                        <div className="text-[10px] text-gray-600 mt-0.5">{(forestStats.lowestLoss / 1000).toFixed(0)} kha</div>
                      </div>
                    </div>

                    <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-800 text-[11px] text-gray-500">
                      <div className="font-semibold text-gray-300 mb-1.5">Data Source</div>
                      <div className="space-y-0.5">
                        <div><strong className="text-gray-400">Source:</strong> Global Forest Watch</div>
                        <div><strong className="text-gray-400">Dataset:</strong> {forestStats.dataDescription || 'UMD Hansen et al.'}</div>
                        <div><strong className="text-gray-400">Resolution:</strong> 30m (Landsat)</div>
                      </div>
                    </div>
                  </div>
                </aside>
              )
            )}
          </>
        )}
      </div>

      {/* Chat interface */}
      <div className={`absolute ${isChatExpanded ? 'bottom-0 left-1/2 -translate-x-1/2' : 'bottom-5 left-1/2 -translate-x-1/2'} z-50 w-full max-w-xl px-4 transition-all duration-300`}>
        <div className={`bg-slate-900/95 backdrop-blur-sm ${isChatExpanded ? 'rounded-t-xl' : 'rounded-xl'} shadow-2xl border border-slate-800 overflow-hidden`}>

          {isChatExpanded && chatMessages.length > 0 && (
            <div className="max-h-80 overflow-y-auto p-5 space-y-3 border-b border-white/[0.05]">
              {chatMessages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${msg.role === 'user'
                    ? 'bg-gradient-to-br from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/20'
                    : 'bg-white/[0.03] text-gray-100 border border-white/[0.08] backdrop-blur-sm'
                    }`}>
                    <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))}
              {isLoadingQuery && (
                <div className="flex justify-start">
                  <div className="bg-white/[0.03] border border-white/[0.08] backdrop-blur-sm rounded-2xl px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-cyan-400 border-t-transparent"></div>
                      <span className="text-[15px] text-gray-300">Analyzing...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="p-4 bg-white/[0.02]">
            <div className="relative flex items-center gap-3 bg-white/[0.03] border border-white/[0.08] rounded-xl p-2.5 shadow-lg hover:border-white/[0.12] focus-within:border-cyan-500/40 transition-all">

              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !isLoadingQuery && handleSendQuery()}
                onFocus={() => setIsChatExpanded(true)}
                placeholder="Ask about urban growth, water changes, deforestation, fires..."
                className="flex-1 h-11 px-4 bg-transparent text-[15px] text-gray-100 placeholder:text-gray-500 focus:outline-none"
                disabled={isLoadingQuery}
              />

              <div className="flex items-center gap-2">
                {isChatExpanded && (
                  <button
                    onClick={() => setIsChatExpanded(false)}
                    className="h-9 w-9 bg-white/[0.05] hover:bg-white/[0.08] rounded-lg flex items-center justify-center transition-colors"
                  >
                    <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                )}

                <button
                  onClick={handleSendQuery}
                  disabled={isLoadingQuery || !chatInput.trim()}
                  className="h-9 w-9 bg-gradient-to-br from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:from-gray-700 disabled:to-gray-700 rounded-lg flex items-center justify-center transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg hover:shadow-cyan-500/30 disabled:shadow-none"
                >
                  {isLoadingQuery ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                  ) : (
                    <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div >
  );
}