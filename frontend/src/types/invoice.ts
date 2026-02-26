// Mirror of backend/app/schemas/invoice.py + frontend state types

// --- API response types ---

export interface IngredientSuggestion {
  id: number;
  name: string;
  score: number;
}

export interface InvoiceLineResponse {
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
  matched_ingredient_id: number | null;
  matched_ingredient_name: string | null;
  match_confidence: string;
  suggestions: IngredientSuggestion[];
}

export interface InvoiceUploadResponse {
  invoice_id: number;
  supplier_name: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  total_excl_vat: number | null;
  total_incl_vat: number | null;
  lines: InvoiceLineResponse[];
  format: string;
  status: string;
  raw_text: string | null;
}

export interface InvoiceListItem {
  id: number;
  supplier_name: string | null;
  invoice_date: string | null;
  source: string;
  format: string;
  status: string;
  total_amount: number | null;
  lines_count: number;
  created_at: string;
}

export interface InvoiceListResponse {
  items: InvoiceListItem[];
  total: number;
}

export interface InvoiceDetailResponse {
  id: number;
  supplier_name: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  source: string;
  format: string;
  status: string;
  total_amount: number | null;
  lines: InvoiceLineResponse[];
  raw_text: string | null;
  created_at: string;
}

export interface InvoiceConfirmResponse {
  prices_updated: number;
  ingredients_created: number;
  aliases_saved: number;
  recipes_recalculated: number;
  recipes_created: number;
}

export interface RecipeLinkRequest {
  recipe_id?: number;
  create_recipe_name?: string;
  create_recipe_price?: number;
  create_recipe_category?: string;
  create_recipe_is_homemade?: boolean;
  quantity?: number;
  unit?: string;
}

export interface InvoiceConfirmLine {
  description: string;
  ingredient_id: number | null;
  create_ingredient_name: string | null;
  unit_price: number | null;
  unit: string | null;
  recipe_links?: RecipeLinkRequest[];
}

// --- Frontend state types (for InvoiceReview) ---

export interface RecipeLinkState {
  recipe_id: number | null;
  recipe_name: string;
  quantity: number;
  unit: string;
  is_new: boolean;
  create_recipe_name?: string;
  create_recipe_price?: number;
  create_recipe_category?: string;
  create_recipe_is_homemade?: boolean;
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
  suggestions: IngredientSuggestion[];
  is_manual: boolean;
  recipe_links: RecipeLinkState[];
}

export type IngredientItem = { id: number; name: string };

export const RECIPE_CATEGORIES = ['entrée', 'plat', 'dessert', 'boisson', 'autre'];
