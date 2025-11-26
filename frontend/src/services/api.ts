/**
 * GEOWISE API Client
 * Axios-based client for communicating with FastAPI backend
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  FireDetection,
  FireAggregationCell,
  FireQueryParams,
  ForestStats,
  TileLayerConfig,
  MPCQueryRequest,
  MPCQueryResponse,
  NLQueryRequest,
  NLQueryResponse,
  GeoJSONFeatureCollection,
  StatsData,
} from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_V1 = process.env.NEXT_PUBLIC_API_V1 || '/api/v1';

class GEOWISEAPIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_URL}${API_V1}`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('[API Error]', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // =========================================================================
  // FIRE ENDPOINTS
  // =========================================================================

  /**
   * Query fire detections with filters
   */
  async getFires(params: FireQueryParams = {}) {
    const response = await this.client.get<{
      fires: FireDetection[];
      pagination: any;
      summary: any;
    }>('/fires', { params });
    return response.data;
  }

  /**
   * Get aggregated fires by H3 hexagons
   */
  async getFireAggregation(params: {
    resolution?: number;
    min_lat?: number;
    min_lon?: number;
    max_lat?: number;
    max_lon?: number;
    start_date?: string;
    end_date?: string;
    days?: number;
  } = {}) {
    const response = await this.client.post<{
      cells: FireAggregationCell[];
      metadata: any;
      summary: any;
    }>('/fires/aggregate', null, { params });
    return response.data;
  }

  /**
   * Get fire statistics
   */
  async getFireStats(startDate: string, endDate: string) {
    const response = await this.client.get<StatsData>('/fires/stats', {
      params: { start_date: startDate, end_date: endDate },
    });
    return response.data;
  }

  /**
   * Get fire density as GeoJSON tiles
   */
  async getFireDensityTiles(params: {
    resolution?: number;
    start_date?: string;
    end_date?: string;
    days?: number;
  } = {}) {
    const response = await this.client.get<GeoJSONFeatureCollection>(
      '/tiles/fire-density',
      { params }
    );
    return response.data;
  }

  /**
   * Get heatmap data
   */
  async getHeatmapData(params: {
    resolution?: number;
    days?: number;
  } = {}) {
    const response = await this.client.get<{
      type: string;
      data: number[][];
      metadata: any;
    }>('/tiles/heatmap', { params });
    return response.data;
  }

  // =========================================================================
  // FOREST ENDPOINTS
  // =========================================================================

  /**
   * Get forest loss data for a country
   */
  async getForestLoss(
    countryISO: string,
    startYear?: number,
    endYear?: number
  ) {
    const response = await this.client.get<ForestStats>(
      `/forest/loss/${countryISO}`,
      {
        params: {
          start_year: startYear,
          end_year: endYear,
        },
      }
    );
    return response.data;
  }

  /**
   * Get comprehensive forest statistics
   */
  async getForestStats(countryISO: string) {
    const response = await this.client.get<ForestStats>(
      `/forest/stats/${countryISO}`
    );
    return response.data;
  }

  /**
   * Get deforestation trend analysis
   */
  async getForestTrend(countryISO: string) {
    const response = await this.client.get<any>(`/forest/trend/${countryISO}`);
    return response.data;
  }

  /**
   * Get forest tile configuration for map visualization
   */
  async getForestTiles() {
    const response = await this.client.get<{
      tile_layers: Record<string, TileLayerConfig>;
      usage_instructions: string;
    }>('/forest/tiles');
    return response.data;
  }

  // =========================================================================
  // MPC ENDPOINTS
  // =========================================================================

  /**
   * Query MPC for land use data
   */
  async queryMPC(request: MPCQueryRequest) {
    const response = await this.client.post<MPCQueryResponse>(
      '/mpc/query',
      request
    );
    return response.data;
  }

  /**
   * Get MPC data coverage information
   */
  async getMPCCoverage() {
    const response = await this.client.get<any>('/mpc/coverage');
    return response.data;
  }

  // =========================================================================
  // AI QUERY ENDPOINTS
  // =========================================================================

  /**
   * Submit natural language query
   */
  async submitNLQuery(request: NLQueryRequest) {
    const response = await this.client.post<NLQueryResponse>(
      '/query/nl',
      request
    );
    return response.data;
  }

  /**
   * Get example queries
   */
  async getQueryExamples() {
    const response = await this.client.get<any>('/query/examples');
    return response.data;
  }

  // =========================================================================
  // HEALTH CHECK
  // =========================================================================

  /**
   * Check API health
   */
  async healthCheck() {
    const response = await this.client.get('/health');
    return response.data;
  }
}

// Export singleton instance
export const api = new GEOWISEAPIClient();
export default api;