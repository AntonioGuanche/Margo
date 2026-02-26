import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type {
  RecipeDetail,
  RecipeListResponse,
  DashboardResponse,
  RecipeCreateRequest,
  RecipeUpdateRequest,
} from '../types';

// Re-export for consumers who import from hook
export type { RecipeListItem } from '../types';

export function useRecipes(search?: string, sortBy?: string, sortOrder?: string) {
  return useQuery({
    queryKey: ['recipes', search, sortBy, sortOrder],
    staleTime: 5 * 60_000, // 5 min — lists change rarely
    queryFn: () => {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (sortBy) params.set('sort_by', sortBy);
      if (sortOrder) params.set('sort_order', sortOrder);
      params.set('limit', '500');
      const qs = params.toString();
      return apiClient<RecipeListResponse>(`/api/recipes${qs ? `?${qs}` : ''}`);
    },
  });
}

export function useRecipe(id: number | null) {
  return useQuery({
    queryKey: ['recipe', id],
    queryFn: () => apiClient<RecipeDetail>(`/api/recipes/${id}`),
    enabled: id !== null,
  });
}

export function useCreateRecipe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RecipeCreateRequest) =>
      apiClient<RecipeDetail>('/api/recipes', { method: 'POST', body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useUpdateRecipe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: RecipeUpdateRequest }) =>
      apiClient<RecipeDetail>(`/api/recipes/${id}`, { method: 'PUT', body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['recipe'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useDeleteRecipe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiClient<void>(`/api/recipes/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useDeleteAllRecipes() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await apiClient<void>('/api/recipes/all', { method: 'DELETE' });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    staleTime: 2 * 60_000, // 2 min
    queryFn: () => apiClient<DashboardResponse>('/api/recipes/dashboard/overview'),
  });
}
