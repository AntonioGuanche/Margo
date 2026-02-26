import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { RestaurantInfo, RestaurantList, SwitchResponse } from '../types';

// Re-export for consumers who import from hook
export type { RestaurantInfo } from '../types';

export function useRestaurants() {
  return useQuery<RestaurantList>({
    queryKey: ['restaurants'],
    queryFn: () => apiClient<RestaurantList>('/api/restaurants'),
  });
}

export async function createSubRestaurant(name: string): Promise<RestaurantInfo> {
  return apiClient<RestaurantInfo>('/api/restaurants', {
    method: 'POST',
    body: { name },
  });
}

export async function switchRestaurant(restaurantId: number): Promise<SwitchResponse> {
  return apiClient<SwitchResponse>(`/api/restaurants/${restaurantId}/switch`);
}

export async function updateRestaurant(
  restaurantId: number,
  data: { name?: string; default_target_margin?: number }
): Promise<RestaurantInfo> {
  return apiClient<RestaurantInfo>(`/api/restaurants/${restaurantId}`, {
    method: 'PUT',
    body: data,
  });
}
