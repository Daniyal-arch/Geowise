/**
 * TypeScript types for Google Earth Engine integration
 * WITH DRIVER LAYER SUPPORT + BOUNDARY VISUALIZATION
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

// 🟢 Driver category information
export interface DriverCategory {
  name: string;
  color: string;
  description: string;
}

// 🟢 Driver tiles response
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
  drivers: boolean; // 🟢 Driver layer visibility
}

// Layer opacity state (UPDATED with drivers)
export interface LayerOpacity {
  baseline: number;
  loss: number;
  gain: number;
  drivers: number; // 🟢 Driver layer opacity
}

// GEE Health check response
export interface GEEHealthResponse {
  status: string;
  message: string;
  initialized: boolean;
  project_id?: string;
}

// 🟢 Country boundary visualization options
export interface BoundaryStyle {
  lineColor: string;      // Border color (e.g., '#FFFFFF')
  lineWidth: number;      // Border width in pixels
  lineOpacity: number;    // Border opacity (0-1)
  fillColor?: string;     // Optional fill color
  fillOpacity?: number;   // Optional fill opacity (0-1)
}

// 🟢 UPDATED: Professional boundary styles (white border, subtle fill)
export const DEFAULT_BOUNDARY_STYLE: BoundaryStyle = {
  lineColor: '#FFFFFF',   // Clean white border
  lineWidth: 2.5,         // Medium thickness
  lineOpacity: 0.85,      // Slightly transparent
  fillColor: '#3B82F6',   // Blue fill
  fillOpacity: 0.08       // Very subtle (8%)
};

// 🟢 Alternative styles you can use
export const BOUNDARY_STYLES = {
  // Professional white border (default)
  professional: {
    lineColor: '#FFFFFF',
    lineWidth: 2.5,
    lineOpacity: 0.85,
    fillColor: '#3B82F6',
    fillOpacity: 0.08
  },
  
  // Bright highlight (original cyan)
  bright: {
    lineColor: '#00FFFF',
    lineWidth: 3,
    lineOpacity: 0.9,
    fillColor: '#FFFF00',
    fillOpacity: 0.05
  },
  
  // Subtle gray
  subtle: {
    lineColor: '#E5E7EB',
    lineWidth: 2,
    lineOpacity: 0.7,
    fillColor: '#9CA3AF',
    fillOpacity: 0.05
  },
  
  // Red alert
  alert: {
    lineColor: '#EF4444',
    lineWidth: 2.5,
    lineOpacity: 0.9,
    fillColor: '#FEE2E2',
    fillOpacity: 0.1
  }
};