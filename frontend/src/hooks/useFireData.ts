/**
 * GEOWISE Fire Data Hook
 * React Query hook for fetching fire detection data
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import api from '@/services/api';
import type { FireQueryParams } from '@/services/types';

export function useFireData(params: FireQueryParams = {}, enabled = true) {
  return useQuery({
    queryKey: ['fires', params],
    queryFn: () => api.getFires(params),
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useFireAggregation(
  params: {
    resolution?: number;
    min_lat?: number;
    min_lon?: number;
    max_lat?: number;
    max_lon?: number;
    start_date?: string;
    end_date?: string;
    days?: number;
  } = {},
  enabled = true
) {
  return useQuery({
    queryKey: ['fire-aggregation', params],
    queryFn: () => api.getFireAggregation(params),
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

export function useFireDensityTiles(
  params: {
    resolution?: number;
    start_date?: string;
    end_date?: string;
    days?: number;
  } = {},
  enabled = true
) {
  return useQuery({
    queryKey: ['fire-density-tiles', params],
    queryFn: () => api.getFireDensityTiles(params),
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

export function useFireStats(startDate: string, endDate: string, enabled = true) {
  return useQuery({
    queryKey: ['fire-stats', startDate, endDate],
    queryFn: () => api.getFireStats(startDate, endDate),
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

export function useHeatmapData(
  params: {
    resolution?: number;
    days?: number;
  } = {},
  enabled = true
) {
  return useQuery({
    queryKey: ['heatmap', params],
    queryFn: () => api.getHeatmapData(params),
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}