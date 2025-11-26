/**
 * Main GEE Service - API Client
 * Handles all communication with GEE backend
 * Location: frontend/src/services/geeService.ts
 */

import type { GEEHealthResponse, HansenForestTiles } from '@/types/gee';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const GEE_API_BASE = `${API_BASE_URL}/api/v1/gee`;

/**
 * Check GEE service health
 */
export async function checkGEEHealth(): Promise<GEEHealthResponse> {
  try {
    const response = await fetch(`${GEE_API_BASE}/health`);
    
    if (!response.ok) {
      throw new Error(`GEE health check failed: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('[GEE Service] Health check error:', error);
    throw error;
  }
}

/**
 * Get Hansen Forest Change tiles for a country
 * @param countryISO - 3-letter country code (e.g., 'BRA', 'IDN', 'PAK')
 * @param forceRefresh - Force regeneration of tiles (bypass cache)
 */
export async function getHansenForestTiles(
  countryISO: string,
  forceRefresh: boolean = false
): Promise<HansenForestTiles> {
  try {
    const url = new URL(`${GEE_API_BASE}/tiles/${countryISO.toUpperCase()}`);
    
    if (forceRefresh) {
      url.searchParams.append('force_refresh', 'true');
    }
    
    console.log('[GEE Service] Fetching Hansen tiles for:', countryISO);
    
    const response = await fetch(url.toString());
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `Failed to fetch tiles: ${response.status}`
      );
    }
    
    const data = await response.json();
    
    console.log('[GEE Service] ✅ Tiles received:', data);
    
    return data;
  } catch (error) {
    console.error('[GEE Service] Error fetching Hansen tiles:', error);
    throw error;
  }
}

/**
 * Utility: Validate country ISO code
 */
export function isValidCountryISO(code: string): boolean {
  return /^[A-Z]{3}$/.test(code.toUpperCase());
}