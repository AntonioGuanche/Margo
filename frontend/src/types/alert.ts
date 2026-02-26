// Mirror of backend/app/schemas/alert.py

export interface AlertItem {
  id: number;
  alert_type: string;
  severity: string;
  message: string;
  details: Record<string, unknown> | null;
  is_read: boolean;
  ingredient_id: number | null;
  recipe_id: number | null;
  created_at: string;
}

export interface AlertListResponse {
  items: AlertItem[];
  total: number;
  unread_count: number;
}

export interface AlertCountResponse {
  unread_count: number;
}
