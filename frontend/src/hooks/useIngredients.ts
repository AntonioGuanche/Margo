import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';

export type UnitType = 'g' | 'kg' | 'cl' | 'l' | 'piece';

export interface Ingredient {
  id: number;
  name: string;
  unit: UnitType;
  current_price: number | null;
  supplier_name: string | null;
  last_updated: string | null;
  created_at: string;
}

interface IngredientListResponse {
  items: Ingredient[];
  total: number;
}

interface IngredientCreate {
  name: string;
  unit: UnitType;
  current_price?: number | null;
  supplier_name?: string | null;
}

interface IngredientUpdate {
  name?: string;
  unit?: UnitType;
  current_price?: number | null;
  supplier_name?: string | null;
}

export function useIngredients(search?: string) {
  return useQuery({
    queryKey: ['ingredients', search],
    queryFn: () => {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      params.set('limit', '200');
      const qs = params.toString();
      return apiClient<IngredientListResponse>(`/api/ingredients${qs ? `?${qs}` : ''}`);
    },
  });
}

export function useCreateIngredient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IngredientCreate) =>
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
    mutationFn: ({ id, data }: { id: number; data: IngredientUpdate }) =>
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
