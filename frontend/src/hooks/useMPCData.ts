/**
 * GEOWISE MPC Data Hook
 * React Query hook for Microsoft Planetary Computer land use data
 */

'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import api from '@/services/api';
import type { MPCQueryRequest } from '@/services/types';

export function useMPCQuery() {
  return useMutation({
    mutationFn: (request: MPCQueryRequest) => api.queryMPC(request),
  });
}

export function useMPCCoverage(enabled = true) {
  return useQuery({
    queryKey: ['mpc-coverage'],
    queryFn: () => api.getMPCCoverage(),
    enabled,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

/**
 * Hook for querying MPC data for multiple regions
 */
export function useMPCBatchQuery(requests: MPCQueryRequest[]) {
  return useQuery({
    queryKey: ['mpc-batch', requests],
    queryFn: async () => {
      return Promise.all(requests.map((req) => api.queryMPC(req)));
    },
    enabled: requests.length > 0,
    staleTime: 60 * 60 * 1000, // 1 hour
  });
}