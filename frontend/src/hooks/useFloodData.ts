/**
 * GEOWISE Flood Data Hook
 * React Query hook for SAR-based flood detection
 * Location: frontend/src/hooks/useFloodData.ts
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  detectFlood,
  detectFloodQuick,
  getAdminLevels,
  getDistricts,
  checkFloodHealth,
  getFloodExamples,
} from '@/services/floodService';
import type { FloodDetectionRequest } from '@/types/flood';

/**
 * Hook for flood detection mutation
 * Use this when detecting floods from user input
 */
export function useFloodDetection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: FloodDetectionRequest) => detectFlood(request),
    onSuccess: (data) => {
      // Cache the result
      if (data.success && data.location?.name) {
        queryClient.setQueryData(
          ['flood', data.location.name, data.dates?.after?.start],
          data
        );
      }
    },
  });
}

/**
 * Hook for quick flood detection (GET request)
 */
export function useFloodDetectionQuick(
  params: {
    location: string;
    location_type: string;
    country?: string;
    before_start: string;
    before_end: string;
    after_start: string;
    after_end: string;
    buffer_km?: number;
  } | null,
  enabled = true
) {
  return useQuery({
    queryKey: ['flood-quick', params],
    queryFn: () => (params ? detectFloodQuick(params) : Promise.reject('No params')),
    enabled: enabled && !!params,
    staleTime: 30 * 60 * 1000, // 30 minutes (flood data doesn't change frequently)
    gcTime: 60 * 60 * 1000, // 1 hour cache
  });
}

/**
 * Hook for getting admin levels (provinces/states) for a country
 */
export function useAdminLevels(country: string | null, enabled = true) {
  return useQuery({
    queryKey: ['admin-levels', country],
    queryFn: () => (country ? getAdminLevels(country) : Promise.reject('No country')),
    enabled: enabled && !!country,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours (admin boundaries don't change)
  });
}

/**
 * Hook for getting districts for a province
 */
export function useDistricts(
  country: string | null,
  province: string | null,
  enabled = true
) {
  return useQuery({
    queryKey: ['districts', country, province],
    queryFn: () =>
      country && province
        ? getDistricts(country, province)
        : Promise.reject('Missing params'),
    enabled: enabled && !!country && !!province,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

/**
 * Hook for checking flood service health
 */
export function useFloodHealth(enabled = true) {
  return useQuery({
    queryKey: ['flood-health'],
    queryFn: checkFloodHealth,
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 60 * 1000, // Refetch every minute
  });
}

/**
 * Hook for getting flood example queries
 */
export function useFloodExamples(enabled = true) {
  return useQuery({
    queryKey: ['flood-examples'],
    queryFn: getFloodExamples,
    enabled,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

/**
 * Hook for storing current flood result in state
 * This is useful for sharing flood data across components
 */
export function useFloodResult(
  locationName: string | null,
  afterDate: string | null
) {
  return useQuery({
    queryKey: ['flood', locationName, afterDate],
    enabled: false, // Only used for reading cached data
    staleTime: Infinity,
  });
}