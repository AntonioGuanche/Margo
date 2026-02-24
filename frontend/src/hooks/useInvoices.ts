import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';

// --- Types ---

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

interface InvoiceListResponse {
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

interface InvoiceConfirmLine {
  description: string;
  ingredient_id: number | null;
  create_ingredient_name: string | null;
  unit_price: number | null;
  unit: string | null;
  add_to_recipe_id?: number;
  recipe_quantity?: number;
  recipe_unit?: string;
  create_recipe_name?: string;
  create_recipe_price?: number;
  create_recipe_category?: string;
  create_recipe_is_homemade?: boolean;
}

interface InvoiceConfirmResponse {
  prices_updated: number;
  ingredients_created: number;
  aliases_saved: number;
  recipes_recalculated: number;
  recipes_created: number;
}

// --- Hooks ---

export function useInvoices(status?: string) {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  const qs = params.toString();

  return useQuery<InvoiceListResponse>({
    queryKey: ['invoices', status],
    queryFn: () => apiClient<InvoiceListResponse>(`/api/invoices${qs ? `?${qs}` : ''}`),
  });
}

export function useInvoice(id: number | string | undefined) {
  return useQuery<InvoiceDetailResponse>({
    queryKey: ['invoices', id],
    queryFn: () => apiClient<InvoiceDetailResponse>(`/api/invoices/${id}`),
    enabled: !!id,
  });
}

export function useUploadInvoice() {
  const queryClient = useQueryClient();

  return useMutation<InvoiceUploadResponse, Error, File>({
    mutationFn: async (file: File) => {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/invoices/upload', {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      });

      if (response.status === 401) {
        localStorage.removeItem('token');
        window.location.href = '/login';
        throw new Error('Session expirée');
      }

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Erreur serveur' }));
        throw new Error(error.detail ?? 'Erreur serveur');
      }

      return response.json() as Promise<InvoiceUploadResponse>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
    },
  });
}

export function useConfirmInvoice(invoiceId: number | string) {
  const queryClient = useQueryClient();

  return useMutation<InvoiceConfirmResponse, Error, InvoiceConfirmLine[]>({
    mutationFn: (lines: InvoiceConfirmLine[]) =>
      apiClient<InvoiceConfirmResponse>(`/api/invoices/${invoiceId}/confirm`, {
        method: 'POST',
        body: { lines },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      queryClient.invalidateQueries({ queryKey: ['ingredients'] });
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function usePatchInvoice(invoiceId: number | string) {
  const queryClient = useQueryClient();

  return useMutation<InvoiceDetailResponse, Error, { supplier_name?: string; invoice_date?: string }>({
    mutationFn: (body) =>
      apiClient<InvoiceDetailResponse>(`/api/invoices/${invoiceId}`, {
        method: 'PATCH',
        body,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices', String(invoiceId)] });
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
    },
  });
}

export function useDeleteInvoice() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, number>({
    mutationFn: (id: number) =>
      apiClient<void>(`/api/invoices/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
    },
  });
}
