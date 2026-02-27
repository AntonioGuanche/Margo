/* Admin types — mirrors backend admin router responses. */

export interface AdminStats {
  total_restaurants: number;
  active_7d: number;
  active_30d: number;
  plans: Record<string, number>;
  total_recipes: number;
  total_ingredients: number;
  total_invoices: number;
  confirmed_invoices: number;
}

export interface AdminUser {
  id: number;
  name: string;
  owner_email: string;
  plan: string;
  created_at: string;
  updated_at: string | null;
  recipes_count: number;
  ingredients_count: number;
  invoices_count: number;
}

export interface AdminUsersResponse {
  users: AdminUser[];
}

export interface AdminCheckResponse {
  is_admin: boolean;
}

export interface NormalizeUnitsResponse {
  ingredients_fixed: number;
  ingredients_total: number;
  recipes_recalculated: number;
  details: Array<{
    name: string;
    old_unit: string;
    old_price: number | null;
    new_unit: string;
    new_price: number | null;
  }>;
}
