import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { SimulateResponse, SimulateRequest } from '../types';

// Re-export for consumers who import from hook
export type { SimulateResponse, SimulatedIngredient, SimulationState } from '../types';

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
