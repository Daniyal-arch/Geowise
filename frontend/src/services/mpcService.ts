/**
 * MPC Service
 * Handles Microsoft Planetary Computer API calls
 * Location: frontend/src/services/mpcService.ts
 */

import type { MPCSearchResponse } from '@/types/mpc';

const API_BASE_URL = 'http://localhost:8000/api/v1';

/**
 * Search MPC for satellite imagery (direct API call - not used if using NLP)
 * This is here for future direct API access if needed
 */
export async function searchMPCImages(params: {
  location_name: string;
  collection?: string;
  start_date?: string;
  end_date?: string;
  max_cloud_cover?: number;
  limit?: number;
  country_hint?: string;
}): Promise<MPCSearchResponse> {
  const url = `${API_BASE_URL}/mpc/search`;
  
  console.log('[MPC Service] Searching images:', params);
  
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }
  
  const data = await response.json();
  
  console.log('[MPC Service] ✅ Images found:', data.images_found);
  
  return data;
}

/**
 * Get collection info
 */
export function getCollectionInfo(collection: string) {
  const collections: Record<string, any> = {
    'sentinel-2-l2a': {
      name: 'Sentinel-2 Level-2A',
      resolution: '10-30m',
      revisit: '5 days',
      description: 'ESA optical imagery with atmospheric correction',
    },
    'landsat-c2-l2': {
      name: 'Landsat Collection 2 Level-2',
      resolution: '30m',
      revisit: '16 days',
      description: 'NASA/USGS optical imagery with surface reflectance',
    },
    'hls': {
      name: 'Harmonized Landsat Sentinel-2 (HLS)',
      resolution: '30m',
      revisit: '2-3 days',
      description: 'Combined Landsat + Sentinel-2 dataset',
    },
  };
  
  return collections[collection] || null;
}

/**
 * Get MPC Explorer URL for an image
 */
export function getMPCExplorerURL(collection: string, itemId: string): string {
  return `https://planetarycomputer.microsoft.com/explore?collection=${collection}&item=${itemId}`;
}

/**
 * Format cloud cover percentage
 */
export function formatCloudCover(cloudCover: number | null): string {
  if (cloudCover === null) return 'N/A';
  return `${cloudCover.toFixed(1)}%`;
}

/**
 * Get cloud cover quality class
 */
export function getCloudQuality(cloudCover: number | null): 'excellent' | 'good' | 'poor' | 'unknown' {
  if (cloudCover === null) return 'unknown';
  if (cloudCover < 10) return 'excellent';
  if (cloudCover < 30) return 'good';
  return 'poor';
}