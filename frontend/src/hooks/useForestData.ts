/**
 * GEOWISE Forest Data Hook
 * React Query hook for fetching forest monitoring data
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import api from '@/services/api';

export function useForestLoss(
  countryISO: string,
  startYear?: number,
  endYear?: number,
  enabled = true
) {
  return useQuery({
    queryKey: ['forest-loss', countryISO, startYear, endYear],
    queryFn: () => api.getForestLoss(countryISO, startYear, endYear),
    enabled: enabled && !!countryISO,
    staleTime: 60 * 60 * 1000, // 1 hour (forest data changes slowly)
  });
}

export function useForestStats(countryISO: string, enabled = true) {
  return useQuery({
    queryKey: ['forest-stats', countryISO],
    queryFn: () => api.getForestStats(countryISO),
    enabled: enabled && !!countryISO,
    staleTime: 60 * 60 * 1000,
  });
}

export function useForestTrend(countryISO: string, enabled = true) {
  return useQuery({
    queryKey: ['forest-trend', countryISO],
    queryFn: () => api.getForestTrend(countryISO),
    enabled: enabled && !!countryISO,
    staleTime: 60 * 60 * 1000,
  });
}

export function useForestTiles(enabled = true) {
  return useQuery({
    queryKey: ['forest-tiles'],
    queryFn: () => api.getForestTiles(),
    enabled,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours (tiles don't change)
  });
}