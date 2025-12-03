/**
 * GEOWISE Frontend TypeScript Types
 * Type definitions for API responses and data structures
 */

// ============================================================================
// FIRE TYPES
// ============================================================================

export interface FireDetection {
  id: string;
  latitude: number;
  longitude: number;
  h3_index_9: string;
  h3_index_5: string;
  brightness: number;
  bright_ti5?: number;
  frp?: number;
  confidence: 'l' | 'n' | 'h';
  satellite?: string;
  instrument?: string;
  acq_date: string;
  acq_time?: string;
  daynight?: string;
}

export interface FireAggregationCell {
  h3_index: string;
  resolution: number;
  fire_count: number;
  total_frp?: number;
  avg_frp?: number;
  max_frp?: number;
  avg_brightness?: number;
  centroid_lat: number;
  centroid_lon: number;
}

export interface FireQueryParams {
  country_iso?: string;
  min_lat?: number;
  min_lon?: number;
  max_lat?: number;
  max_lon?: number;
  start_date?: string;
  end_date?: string;
  days?: number;
  min_frp?: number;
  confidence?: 'l' | 'n' | 'h';
  offset?: number;
  limit?: number;
}

// ============================================================================
// FOREST TYPES
// ============================================================================

export interface YearlyForestLoss {
  year: number;
  loss_hectares: number;
  loss_km2: number;
}

export interface ForestStats {
  country_iso: string;
  country_name: string;
  total_loss_hectares: number;
  total_loss_km2: number;
  data_range: string;
  most_recent_year: number;
  recent_loss_hectares: number;
  yearly_data: YearlyForestLoss[];
  source: string;
}

export interface TileLayerConfig {
  layer_id: string;
  tile_url: string;
  description: string;
  min_zoom: number;
  max_zoom: number;
  attribution?: string;
}

// ============================================================================
// MPC TYPES
// ============================================================================

export interface LandUseClass {
  class_id: number;
  class_name: string;
  pixel_count: number;
  percentage: number;
  color: string;
}

export interface MPCQueryRequest {
  bbox: [number, number, number, number]; // [west, south, east, north]
  year: number;
  region_name: string;
}

export interface MPCQueryResponse {
  status: string;
  region: string;
  year: number;
  bbox: [number, number, number, number];
  land_use_classes: LandUseClass[];
  total_pixels: number;
  resolution: string;
  source: string;
  item_id: string;
  metadata: Record<string, any>;
}

// ============================================================================
// AI QUERY TYPES
// ============================================================================

export interface NLQueryRequest {
  query: string;
  include_raw_data?: boolean;
}

export interface NLQueryResponse {
  status: string;
  query: string;
  intent?: string;
  report?: string;
  data?: Record<string, any>;
  error?: string;
}

// ============================================================================
// GEOJSON TYPES
// ============================================================================

export interface GeoJSONFeature {
  type: 'Feature';
  geometry: {
    type: 'Point' | 'Polygon' | 'MultiPolygon';
    coordinates: number[] | number[][] | number[][][];
  };
  properties: Record<string, any>;
}

export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
  metadata?: Record<string, any>;
}

// ============================================================================
// MAP TYPES
// ============================================================================

export type LayerType = 'fires' | 'forest-loss' | 'forest-gain' | 'mpc-land-use' | 'fire-hexagons';

export interface LayerState {
  id: LayerType;
  name: string;
  visible: boolean;
  opacity: number;
  color: string;
  source?: string;
}

export interface MapState {
  center: [number, number];
  zoom: number;
  bearing: number;
  pitch: number;
}

// ============================================================================
// UI TYPES
// ============================================================================

export interface StatsData {
  total_fires: number;
  avg_frp: number;
  max_frp: number;
  high_confidence_count: number;
  date_range: {
    start: string;
    end: string;
  };
}

export interface QueryFilter {
  country?: string;
  year?: number;
  startDate?: string;
  endDate?: string;
  dataType?: 'fires' | 'forest' | 'mpc';
}