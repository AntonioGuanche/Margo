// Mirror of backend/app/schemas/ingredient.py

export type UnitType = 'g' | 'kg' | 'cl' | 'l' | 'piece';

export interface Ingredient {
  id: number;
  name: string;
  unit: UnitType;
  current_price: number | null;
  supplier_name: string | null;
  category: string | null;
  last_updated: string | null;
  created_at: string;
}

export interface IngredientListResponse {
  items: Ingredient[];
  total: number;
}

export interface IngredientCreateRequest {
  name: string;
  unit: UnitType;
  current_price?: number | null;
  supplier_name?: string | null;
  category?: string | null;
}

export interface IngredientUpdateRequest {
  name?: string;
  unit?: UnitType;
  current_price?: number | null;
  supplier_name?: string | null;
  category?: string | null;
}

export interface PriceHistoryEntry {
  price: number;
  date: string;
  invoice_id: number | null;
  supplier_name: string | null;
  created_at: string;
}

export interface PriceHistoryResponse {
  ingredient_name: string;
  current_price: number | null;
  history: PriceHistoryEntry[];
}

export interface IngredientRecipeItem {
  recipe_id: number;
  recipe_name: string;
  category: string | null;
  quantity: number;
  unit: string;
}
