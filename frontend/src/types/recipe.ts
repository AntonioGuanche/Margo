// Mirror of backend/app/schemas/recipe.py

export type MarginStatus = 'green' | 'orange' | 'red';

export interface RecipeIngredientResponse {
  id: number;
  ingredient_id: number;
  ingredient_name: string;
  quantity: number;
  unit: string;
  unit_cost: number | null;
  unit_cost_unit: string | null;
  line_cost: number | null;
  converted_quantity?: number | null;
  conversion_ok?: boolean;
  supplier_name?: string | null;
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

export interface RecipeDetail extends RecipeListItem {
  ingredients: RecipeIngredientResponse[];
}

export interface RecipeListResponse {
  items: RecipeListItem[];
  total: number;
}

export interface DashboardResponse {
  average_food_cost_percent: number | null;
  total_recipes: number;
  recipes_green: number;
  recipes_orange: number;
  recipes_red: number;
  recipes: RecipeListItem[];
}

export interface RecipeIngredientInput {
  ingredient_id: number;
  quantity: number;
  unit: string;
}

export interface RecipeCreateRequest {
  name: string;
  selling_price: number;
  category?: string | null;
  target_margin?: number | null;
  is_homemade?: boolean;
  ingredients: RecipeIngredientInput[];
}

export interface RecipeUpdateRequest {
  name?: string;
  selling_price?: number;
  category?: string | null;
  target_margin?: number | null;
  is_homemade?: boolean;
  ingredients?: RecipeIngredientInput[];
}
