/**
 * Fire Detection Service
 * Fetches live fire data from NASA FIRMS via backend API
 */

import type { LiveFiresResponse } from '@/types/fires';

const API_BASE_URL = 'http://localhost:8000/api/v1';

/**
 * Get live fires directly from NASA FIRMS API
 * No database needed - real-time data
 */
export async function getLiveFireDetections(
  countryISO: string,
  days: number = 2
): Promise<LiveFiresResponse> {
  const url = `${API_BASE_URL}/fires/live/${countryISO.toUpperCase()}?days=${days}`;
  
  console.log('[Fire Service] Fetching LIVE fires:', countryISO, `(${days} days)`);
  
  const response = await fetch(url);
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }
  
  const data = await response.json();
  
  console.log('[Fire Service] ✅ LIVE fires received:', {
    total: data.statistics.total_fires,
    high_confidence: data.statistics.high_confidence_count,
    avg_frp: data.statistics.frp_statistics.avg.toFixed(2),
    day_fires: data.statistics.day_fires,
    night_fires: data.statistics.night_fires
  });
  
  return data;
}

/**
 * Get confidence color for map markers
 */
export function getConfidenceColor(confidence: 'h' | 'n' | 'l'): string {
  switch (confidence) {
    case 'h': return '#EF4444'; // Red - High confidence
    case 'n': return '#F97316'; // Orange - Nominal
    case 'l': return '#FCD34D'; // Yellow - Low
    default: return '#9CA3AF';  // Gray - Unknown
  }
}

/**
 * Get FRP size for map markers (radius in pixels)
 */
export function getFRPSize(frp: number | undefined): number {
  if (!frp) return 4;
  if (frp < 5) return 4;
  if (frp < 10) return 6;
  if (frp < 20) return 8;
  return 10;
}

/**
 * Get satellite display name
 */
export function getSatelliteName(code: string): string {
  const names: Record<string, string> = {
    'N': 'VIIRS NOAA-20',
    'T': 'MODIS Terra',
    'A': 'MODIS Aqua'
  };
  return names[code] || code;
}