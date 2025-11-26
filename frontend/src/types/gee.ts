/**
 * TypeScript types for Google Earth Engine integration
 * Location: frontend/src/types/gee.ts
 */

// Base GEE API response
export interface GEEResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

// Generic tile layer info
export interface GEETileLayer {
  name: string;
  tile_url: string;
  description: string;
  year_range: string;
}

// Hansen Forest Change tiles response
export interface HansenForestTiles {
  success: boolean;
  country_iso: string;
  country_name: string;
  center: [number, number];
  zoom: number;
  layers: {
    baseline: GEETileLayer;
    loss: GEETileLayer;
    gain: GEETileLayer;
  };
  generated_at: string;
}

// Layer visibility state
export interface LayerVisibility {
  baseline: boolean;
  loss: boolean;
  gain: boolean;
}

// Layer opacity state
export interface LayerOpacity {
  baseline: number;
  loss: number;
  gain: number;
}

// GEE Health check response
export interface GEEHealthResponse {
  status: string;
  message: string;
  initialized: boolean;
  project_id?: string;
}