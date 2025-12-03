/**
 * TypeScript types for Google Earth Engine integration
 * WITH DRIVER LAYER SUPPORT
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

// 🟢 NEW: Driver category information
export interface DriverCategory {
  name: string;
  color: string;
  description: string;
}

// 🟢 NEW: Driver tiles response
export interface DriverTiles {
  success: boolean;
  country_iso: string;
  driver_type: string;
  tile_url: string;
  driver_categories: {
    [key: number]: DriverCategory;
  };
  dataset_info: {
    source: string;
    resolution: string;
    year: string;
    citation: string;
  };
}

// Layer visibility state (UPDATED with drivers)
export interface LayerVisibility {
  baseline: boolean;
  loss: boolean;
  gain: boolean;
  drivers: boolean; // 🟢 NEW: Driver layer visibility
}

// Layer opacity state (UPDATED with drivers)
export interface LayerOpacity {
  baseline: number;
  loss: number;
  gain: number;
  drivers: number; // 🟢 NEW: Driver layer opacity
}

// GEE Health check response
export interface GEEHealthResponse {
  status: string;
  message: string;
  initialized: boolean;
  project_id?: string;
}
// 🟢 NEW: Country boundary visualization options
export interface BoundaryStyle {
  lineColor: string;      // Border color (e.g., '#00FFFF')
  lineWidth: number;      // Border width in pixels
  lineOpacity: number;    // Border opacity (0-1)
  fillColor?: string;     // Optional fill color
  fillOpacity?: number;   // Optional fill opacity (0-1)
}

// 🟢 NEW: Default boundary styles
export const DEFAULT_BOUNDARY_STYLE: BoundaryStyle = {
  lineColor: '#00FFFF',   // Bright cyan
  lineWidth: 3,
  lineOpacity: 0.9,
  fillColor: '#FFFF00',   // Yellow
  fillOpacity: 0.05       // Very subtle
};