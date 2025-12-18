/**
 * Flood Types - v5.2 with Optical Support
 * Location: frontend/src/types/flood.ts
 */

// ============================================================================
// TILE URLS
// ============================================================================

export interface FloodTiles {
  // SAR layers
  flood_extent?: string;
  change_detection?: string;
  sar_before?: string;
  sar_after?: string;
  permanent_water?: string;
  // v5.2: Optical layers
  optical_before?: string;
  optical_after?: string;
  false_color_after?: string;
  ndwi_after?: string;
}

// ============================================================================
// LAYER STATE (visibility toggles)
// ============================================================================

export interface FloodLayerState {
  // SAR layers
  floodExtent: boolean;
  changeDetection: boolean;
  sarBefore: boolean;
  sarAfter: boolean;
  permanentWater: boolean;
  // v5.2: Optical layers
  opticalBefore: boolean;
  opticalAfter: boolean;
  falseColor: boolean;
  ndwi: boolean;
}

// ============================================================================
// LAYER OPACITY
// ============================================================================

export interface FloodLayerOpacity {
  // SAR layers
  floodExtent: number;
  changeDetection: number;
  sarBefore: number;
  sarAfter: number;
  permanentWater: number;
  // v5.2: Optical layers
  opticalBefore: number;
  opticalAfter: number;
  falseColor: number;
  ndwi: number;
}

// ============================================================================
// DEFAULT VALUES
// ============================================================================

export const DEFAULT_FLOOD_LAYERS: FloodLayerState = {
  // SAR layers
  floodExtent: true,
  changeDetection: true,
  sarBefore: false,
  sarAfter: false,
  permanentWater: true,
  // v5.2: Optical layers (off by default until loaded)
  opticalBefore: false,
  opticalAfter: false,
  falseColor: false,
  ndwi: false,
};

export const DEFAULT_FLOOD_OPACITY: FloodLayerOpacity = {
  // SAR layers
  floodExtent: 0.8,
  changeDetection: 0.7,
  sarBefore: 0.8,
  sarAfter: 0.8,
  permanentWater: 0.6,
  // v5.2: Optical layers
  opticalBefore: 0.8,
  opticalAfter: 0.8,
  falseColor: 0.8,
  ndwi: 0.8,
};

// ============================================================================
// STATISTICS
// ============================================================================

export interface FloodStatistics {
  flood_area_km2: number;
  flood_area_ha?: number;
  exposed_population: number;
  flooded_cropland_ha: number;
  flooded_urban_ha: number;
}

// ============================================================================
// METHODOLOGY
// ============================================================================

export interface FloodMethodology {
  sensor: string;
  technique: string;
  resolution: string;
  threshold: string;
}

// ============================================================================
// DATE RANGES
// ============================================================================

export interface FloodDateRange {
  start: string;
  end: string;
}

export interface FloodDates {
  before: FloodDateRange;
  after: FloodDateRange;
}

// ============================================================================
// IMAGES USED
// ============================================================================

export interface FloodImagesUsed {
  before: number;
  after: number;
}

// ============================================================================
// SUGGESTION (for overview responses)
// ============================================================================

export interface FloodSuggestion {
  message?: string;
  sub_regions?: Array<{ name: string; type: string }>;
  next_level_type?: string;
  example_query?: string;
}

// ============================================================================
// OPTICAL AVAILABILITY
// ============================================================================

export interface OpticalAvailability {
  available: boolean;
  cloud_cover_before?: number;
  cloud_cover_after?: number;
  message?: string;
}

// ============================================================================
// MAIN NLP RESPONSE
// ============================================================================

export interface FloodNLPResponse {
  status: string;
  intent: string;
  query: string;
  report: string;
  data: {
    show_flood: boolean;
    location_name: string;
    location_type: string;
    country: string;
    province?: string;
    area_km2?: number;
    center: [number, number];
    zoom: number;
    dates?: FloodDates;
    images_used?: FloodImagesUsed;
    tiles: FloodTiles;
    statistics?: FloodStatistics;
    methodology?: FloodMethodology;
    suggestion?: FloodSuggestion;
    optical_availability?: OpticalAvailability;
    level?: 'overview' | 'detailed';
  };
}

// ============================================================================
// DETECTION REQUEST/RESPONSE (Direct API)
// ============================================================================

export interface FloodDetectionRequest {
  location: string;
  location_type: string;
  country?: string;
  before_start: string;
  before_end: string;
  after_start: string;
  after_end: string;
  buffer_km?: number;
}

export interface FloodDetectionResponse {
  success: boolean;
  location?: {
    name: string;
    type: string;
    country: string;
    province?: string;
    area_km2?: number;
    center: [number, number];
  };
  dates?: FloodDates;
  images_used?: FloodImagesUsed;
  tiles?: FloodTiles;
  statistics?: FloodStatistics;
  methodology?: FloodMethodology;
  error?: string;
}

// ============================================================================
// ADMIN LEVELS
// ============================================================================

export interface AdminLevelsResponse {
  country: string;
  provinces: string[];
}

export interface DistrictListResponse {
  country: string;
  province: string;
  districts: string[];
}

// ============================================================================
// HEALTH CHECK
// ============================================================================

export interface FloodHealthResponse {
  status: string;
  gee_initialized: boolean;
  sentinel1_available: boolean;
  message?: string;
}