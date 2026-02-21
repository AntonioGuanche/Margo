import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';

export interface SimulatedIngredient {
  ingredient_id: number;
  ingredient_name: string;
  quantity: number;
  unit: string;
  unit_price: number | null;
  line_cost: number | null;
  changed: boolean;
}

export interface SimulationState {
  selling_price: number;
  food_cost: number;
  food_cost_percent: number;
  margin_status: string;
  gross_margin: number;
  ingredients: SimulatedIngredient[];
}

export interface SimulateResponse {
  recipe_name: string;
  current: SimulationState;
  simulated: SimulationState;
  monthly_impact: number | null;
}

interface IngredientAdjustment {
  ingredient_id: number;
  new_quantity?: number | null;
  new_unit_price?: number | null;
}

interface SimulateRequest {
  new_selling_price?: number | null;
  ingredient_adjustments?: IngredientAdjustment[] | null;
  estimated_weekly_sales?: number | null;
}

export function useSimulate(recipeId: number) {
  return useMutation({
    mutationFn: (data: SimulateRequest) =>
      apiClient<SimulateResponse>(`/api/recipes/${recipeId}/simulate`, {
        method: 'POST',
        body: data,
      }),
  });
}

export function useApplySimulation(recipeId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SimulateRequest) =>
      apiClient<SimulateResponse>(`/api/recipes/${recipeId}/apply-simulation`, {
        method: 'POST',
        body: data,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['recipe'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}
