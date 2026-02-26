import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';

export type MarginStatus = 'green' | 'orange' | 'red';

export interface RecipeIngredient {
  id: number;
  ingredient_id: number;
  ingredient_name: string;
  quantity: number;
  unit: string;
  unit_cost: number | null;
  unit_cost_unit: string | null;
  line_cost: number | null;
}

export interface RecipeListItem {
  id: number;
  name: string;
  selling_price: number;
  category: string | null;
  target_margin: number | null;
  food_cost: number | null;
  food_cost_percent: number | null;
  is_homemade: boolean;
  margin_status: MarginStatus;
  created_at: string;
}

export interface Recipe extends RecipeListItem {
  ingredients: RecipeIngredient[];
}

interface RecipeListResponse {
  items: RecipeListItem[];
  total: number;
}

export interface DashboardData {
  average_food_cost_percent: number | null;
  total_recipes: number;
  recipes_green: number;
  recipes_orange: number;
  recipes_red: number;
  recipes: RecipeListItem[];
}

interface RecipeIngredientInput {
  ingredient_id: number;
  quantity: number;
  unit: string;
}

interface RecipeCreate {
  name: string;
  selling_price: number;
  category?: string | null;
  target_margin?: number | null;
  is_homemade?: boolean;
  ingredients: RecipeIngredientInput[];
}

interface RecipeUpdate {
  name?: string;
  selling_price?: number;
  category?: string | null;
  target_margin?: number | null;
  is_homemade?: boolean;
  ingredients?: RecipeIngredientInput[];
}

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
    queryFn: () => apiClient<Recipe>(`/api/recipes/${id}`),
    enabled: id !== null,
  });
}

export function useCreateRecipe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RecipeCreate) =>
      apiClient<Recipe>('/api/recipes', { method: 'POST', body: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useUpdateRecipe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: RecipeUpdate }) =>
      apiClient<Recipe>(`/api/recipes/${id}`, { method: 'PUT', body: data }),
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
    queryFn: () => apiClient<DashboardData>('/api/recipes/dashboard/overview'),
  });
}
