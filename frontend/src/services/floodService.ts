/**
 * Flood Detection Service
 * API calls for SAR-based flood detection
 * Location: frontend/src/services/floodService.ts
 */

import type {
  FloodDetectionRequest,
  FloodDetectionResponse,
  AdminLevelsResponse,
  DistrictListResponse,
  FloodHealthResponse,
} from '@/types/flood';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_V1 = '/api/v1';

/**
 * Detect floods using SAR change detection
 */
export async function detectFlood(
  request: FloodDetectionRequest
): Promise<FloodDetectionResponse> {
  const url = `${API_BASE_URL}${API_V1}/floods/detect`;

  console.log('[Flood Service] Detecting floods:', request);

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  const data = await response.json();

  if (data.success) {
    console.log('[Flood Service] ✅ Flood detection complete:', {
      location: data.location?.name,
      area_km2: data.statistics?.area_km2,
      population: data.statistics?.exposed_population,
    });
  } else {
    console.warn('[Flood Service] ⚠️ Detection failed:', data.error);
  }

  return data;
}

/**
 * Quick flood detection via GET (for testing)
 */
export async function detectFloodQuick(params: {
  location: string;
  location_type: string;
  country?: string;
  before_start: string;
  before_end: string;
  after_start: string;
  after_end: string;
  buffer_km?: number;
}): Promise<FloodDetectionResponse> {
  const searchParams = new URLSearchParams();
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  });

  const url = `${API_BASE_URL}${API_V1}/floods/detect/quick?${searchParams}`;

  console.log('[Flood Service] Quick detection:', params.location);

  const response = await fetch(url);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Get available provinces/states for a country
 */
export async function getAdminLevels(country: string): Promise<AdminLevelsResponse> {
  const url = `${API_BASE_URL}${API_V1}/floods/admin/${encodeURIComponent(country)}`;

  console.log('[Flood Service] Getting admin levels for:', country);

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Get districts for a province
 */
export async function getDistricts(
  country: string,
  province: string
): Promise<DistrictListResponse> {
  const url = `${API_BASE_URL}${API_V1}/floods/districts/${encodeURIComponent(country)}/${encodeURIComponent(province)}`;

  console.log('[Flood Service] Getting districts for:', province, country);

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Check flood service health
 */
export async function checkFloodHealth(): Promise<FloodHealthResponse> {
  const url = `${API_BASE_URL}${API_V1}/floods/health`;

  const response = await fetch(url);

  if (!response.ok) {
    return {
      status: 'unhealthy',
      gee_initialized: false,
      sentinel1_available: false,
      message: `HTTP ${response.status}`,
    };
  }

  return response.json();
}

/**
 * Get example flood queries
 */
export async function getFloodExamples(): Promise<any> {
  const url = `${API_BASE_URL}${API_V1}/floods/examples`;

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Format flood area for display
 */
export function formatFloodArea(km2: number): string {
  if (km2 >= 1000) {
    return `${(km2 / 1000).toFixed(1)}K km²`;
  }
  return `${km2.toFixed(1)} km²`;
}

/**
 * Format population for display
 */
export function formatPopulation(count: number): string {
  if (count >= 1000000) {
    return `${(count / 1000000).toFixed(2)}M`;
  }
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`;
  }
  return count.toLocaleString();
}

/**
 * Get severity level based on flood extent
 */
export function getFloodSeverity(
  areaKm2: number
): 'minor' | 'moderate' | 'major' | 'severe' {
  if (areaKm2 < 100) return 'minor';
  if (areaKm2 < 500) return 'moderate';
  if (areaKm2 < 2000) return 'major';
  return 'severe';
}

/**
 * Get severity color
 */
export function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'minor':
      return '#3B82F6'; // Blue
    case 'moderate':
      return '#F59E0B'; // Yellow
    case 'major':
      return '#F97316'; // Orange
    case 'severe':
      return '#EF4444'; // Red
    default:
      return '#6B7280'; // Gray
  }
}

/**
 * Get flood layer color
 */
export function getFloodLayerColor(layer: string): string {
  switch (layer) {
    case 'flood_extent':
      return '#FF0000'; // Red
    case 'change_detection':
      return '#0000FF'; // Blue gradient
    case 'sar_before':
      return '#808080'; // Gray
    case 'sar_after':
      return '#404040'; // Dark gray
    case 'permanent_water':
      return '#00FFFF'; // Cyan
    default:
      return '#FFFFFF';
  }
}