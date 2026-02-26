import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { AlertListResponse, AlertCountResponse } from '../types';

// Re-export for consumers who import from hook
export type { AlertItem } from '../types';

export function useAlerts(isRead?: boolean, severity?: string) {
  return useQuery({
    queryKey: ['alerts', isRead, severity],
    queryFn: () => {
      const params = new URLSearchParams();
      if (isRead !== undefined) params.set('is_read', String(isRead));
      if (severity) params.set('severity', severity);
      params.set('limit', '100');
      const qs = params.toString();
      return apiClient<AlertListResponse>(`/api/alerts${qs ? `?${qs}` : ''}`);
    },
  });
}

export function useAlertCount() {
  return useQuery({
    queryKey: ['alert-count'],
    queryFn: () => apiClient<AlertCountResponse>('/api/alerts/count'),
    refetchInterval: 60_000, // Poll every 60 seconds
  });
}

export function useMarkAlertRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiClient<void>(`/api/alerts/${id}/read`, { method: 'PUT' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['alert-count'] });
    },
  });
}

export function useMarkAllRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiClient<void>('/api/alerts/read-all', { method: 'PUT' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['alert-count'] });
    },
  });
}
