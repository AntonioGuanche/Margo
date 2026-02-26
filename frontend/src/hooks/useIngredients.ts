import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type {
  Ingredient,
  IngredientListResponse,
  IngredientCreateRequest,
  IngredientUpdateRequest,
  PriceHistoryResponse,
} from '../types';

// Re-export for consumers who import from hook
export type { Ingredient, UnitType, PriceHistoryEntry } from '../types';

export function useIngredients(search?: string) {
  return useQuery({
    queryKey: ['ingredients', search],
    staleTime: 5 * 60_000, // 5 min — lists change rarely
    queryFn: () => {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      params.set('limit', '500');
      const qs = params.toString();
      return apiClient<IngredientListResponse>(`/api/ingredients${qs ? `?${qs}` : ''}`);
    },
  });
}

export function useCreateIngredient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IngredientCreateRequest) =>
      apiClient<Ingredient>('/api/ingredients', {
        method: 'POST',
        body: data,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ingredients'] });
    },
  });
}

export function useUpdateIngredient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: IngredientUpdateRequest }) =>
      apiClient<Ingredient>(`/api/ingredients/${id}`, {
        method: 'PUT',
        body: data,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ingredients'] });
    },
  });
}

export function useDeleteIngredient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiClient<void>(`/api/ingredients/${id}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ingredients'] });
    },
  });
}

export function usePriceHistory(ingredientId: number | undefined) {
  return useQuery<PriceHistoryResponse>({
    queryKey: ['price-history', ingredientId],
    queryFn: () =>
      apiClient<PriceHistoryResponse>(`/api/ingredients/${ingredientId}/price-history`),
    enabled: !!ingredientId,
  });
}
