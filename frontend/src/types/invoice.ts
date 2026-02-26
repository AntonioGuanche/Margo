export type RecipeLinkState = {
  recipe_id: number | null;
  recipe_name: string;
  quantity: number;
  unit: string;
  is_new: boolean;
  // For creation
  create_recipe_name?: string;
  create_recipe_price?: number;
  create_recipe_category?: string;
  create_recipe_is_homemade?: boolean;
};

export interface IngredientRecipeItem {
  recipe_id: number;
  recipe_name: string;
  category: string | null;
  quantity: number;
  unit: string;
}

export interface LineState {
  description: string;
  quantity: number | null;
  unit: string | null;
  unit_price: number | null;
  total_price: number | null;
  units_per_package: number | null;
  volume_liters: number | null;
  serving_type: string | null;
  suggested_serving_cl: number | null;
  suggested_portions: number | null;
  price_per_portion: number | null;
  ingredient_id: number | null;
  create_ingredient_name: string | null;
  ignored: boolean;
  match_confidence: string;
  suggestions: { id: number; name: string; score: number }[];
  is_manual: boolean;
  recipe_links: RecipeLinkState[];
}

export type IngredientItem = { id: number; name: string };

export const RECIPE_CATEGORIES = ['entrée', 'plat', 'dessert', 'boisson', 'autre'];
