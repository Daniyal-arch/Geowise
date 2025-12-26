/**
 * Microsoft Planetary Computer (MPC) Types
 * Satellite imagery search and metadata
 * Location: frontend/src/types/mpc.ts
 */

// ============================================================================
// IMAGE METADATA
// ============================================================================

export interface MPCImage {
  id: string;                    // STAC item ID
  collection: string;            // sentinel-2-l2a, landsat-c2-l2, hls
  datetime: string;              // ISO datetime
  cloud_cover: number | null;    // 0-100 percentage
  geometry?: {
    type: string;
    coordinates: number[][][];
  };
  bbox?: number[];               // [minx, miny, maxx, maxy]
  assets?: Record<string, any>;  // Asset details
    tile_urls?: {
    natural_color?: string;
    false_color?: string;
    ndvi?: string;
  };
}

// ============================================================================
// SEARCH RESPONSE
// ============================================================================

export interface MPCSearchResponse {
  success: boolean;
  location: string;
  bbox: number[];                // [minx, miny, maxx, maxy]
  collection: string;
  collection_name: string;       // Human-readable name
  images_found: number;
  images: MPCImage[];
  query_params: {
    dates: string;               // "2024-08-01 to 2024-08-31"
    max_cloud_cover: number;
    limit: number;
  };
  message: string;
  error?: string;
}

// ============================================================================
// NLP QUERY RESPONSE
// ============================================================================

export interface MPCNLPResponse {
  status: string;
  intent: string;
  data: {
    location: string;
    bbox: number[];
    collection: string;
    center: [number, number];
    zoom: number;
    show_mpc: boolean;
    images_found: number;
    images: MPCImage[];
    query_params: any;
    message: string;
    
    // ✅ Boundary fields
    boundary?: {
      type: string;
      coordinates: number[][][];
    };
    boundary_source?: string;
    area_km2?: number;
  };
  report?: string;
}

// ============================================================================
// COLLECTION INFO
// ============================================================================

export interface MPCCollection {
  id: string;
  name: string;
  description: string;
  resolution: string;
  revisit: string;
  color: string;           // For UI styling
}

export const MPC_COLLECTIONS: Record<string, MPCCollection> = {
  'sentinel-2-l2a': {
    id: 'sentinel-2-l2a',
    name: 'Sentinel-2 L2A',
    description: 'Optical imagery, 10-30m resolution',
    resolution: '10-30m',
    revisit: '5 days',
    color: '#0066cc',
  },
  'landsat-c2-l2': {
    id: 'landsat-c2-l2',
    name: 'Landsat 8/9',
    description: 'Optical imagery, 30m resolution',
    resolution: '30m',
    revisit: '16 days',
    color: '#cc6600',
  },
  'hls': {
    id: 'hls',
    name: 'HLS',
    description: 'Harmonized Landsat Sentinel-2',
    resolution: '30m',
    revisit: '2-3 days',
    color: '#00cc66',
  },
};

// ============================================================================
// LAYER STATE (for map display)
// ============================================================================

export interface MPCLayerState {
  searchArea: boolean;      // Show search bbox polygon
  imageMarkers: boolean;    // Show image count marker
}

export const DEFAULT_MPC_LAYERS: MPCLayerState = {
  searchArea: true,
  imageMarkers: true,
};

// ============================================================================
// STATISTICS (for sidebar)
// ============================================================================

export interface MPCStatistics {
  total_images: number;
  best_image: MPCImage | null;
  avg_cloud_cover: number;
  date_range: string;
  collection_name: string;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get collection color for UI
 */
export function getCollectionColor(collection: string): string {
  return MPC_COLLECTIONS[collection]?.color || '#666666';
}

/**
 * Get cloud cover quality class
 */
export function getCloudCoverClass(cloudCover: number | null): {
  label: string;
  color: string;
  bgClass: string;
} {
  if (cloudCover === null) {
    return { label: 'Unknown', color: '#9CA3AF', bgClass: 'bg-gray-500' };
  }
  
  if (cloudCover < 10) {
    return { label: 'Excellent', color: '#4CAF50', bgClass: 'bg-green-500' };
  } else if (cloudCover < 30) {
    return { label: 'Good', color: '#FF9800', bgClass: 'bg-orange-500' };
  } else {
    return { label: 'Poor', color: '#F44336', bgClass: 'bg-red-500' };
  }
}

/**
 * Format date for display
 */
export function formatImageDate(datetime: string): string {
  try {
    return new Date(datetime).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return datetime;
  }
}

/**
 * Get MPC Explorer URL
 */
export function getMPCExplorerURL(collection: string, itemId: string): string {
  return `https://planetarycomputer.microsoft.com/explore?collection=${collection}&item=${itemId}`;
}