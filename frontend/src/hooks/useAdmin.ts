import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type {
  AdminStats,
  AdminUsersResponse,
  AdminCheckResponse,
  NormalizeUnitsResponse,
} from '../types';

export function useAdminCheck() {
  return useQuery<AdminCheckResponse>({
    queryKey: ['admin', 'check'],
    queryFn: () => apiClient<AdminCheckResponse>('/admin/check'),
    retry: false,
    staleTime: 5 * 60_000, // 5 min — admin status won't change mid-session
  });
}

export function useAdminStats() {
  return useQuery<AdminStats>({
    queryKey: ['admin', 'stats'],
    queryFn: () => apiClient<AdminStats>('/admin/stats'),
  });
}

export function useAdminUsers() {
  return useQuery<AdminUsersResponse>({
    queryKey: ['admin', 'users'],
    queryFn: () => apiClient<AdminUsersResponse>('/admin/users'),
  });
}

export function useUpdateUserPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, plan }: { id: number; plan: string }) =>
      apiClient(`/admin/users/${id}`, {
        method: 'PATCH',
        body: { plan },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin'] });
    },
  });
}

export function useNormalizeUnits() {
  return useMutation({
    mutationFn: (restaurantId: number) =>
      apiClient<NormalizeUnitsResponse>(
        `/admin/users/${restaurantId}/normalize-units`,
        { method: 'POST' },
      ),
  });
}

