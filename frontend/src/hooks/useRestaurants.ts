import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';

interface RestaurantInfo {
  id: number;
  name: string;
  owner_email: string;
  plan: string;
  default_target_margin: number;
  parent_restaurant_id: number | null;
}

interface RestaurantList {
  main: RestaurantInfo;
  sub_restaurants: RestaurantInfo[];
}

interface SwitchResponse {
  access_token: string;
  restaurant_id: number;
  restaurant_name: string;
}

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
