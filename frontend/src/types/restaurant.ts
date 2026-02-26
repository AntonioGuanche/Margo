// Mirror of backend/app/schemas/restaurant.py

export interface RestaurantInfo {
  id: number;
  name: string;
  owner_email: string;
  plan: string;
  default_target_margin: number;
  parent_restaurant_id: number | null;
}

export interface RestaurantList {
  main: RestaurantInfo;
  sub_restaurants: RestaurantInfo[];
}

export interface SwitchResponse {
  access_token: string;
  restaurant_id: number;
  restaurant_name: string;
}
