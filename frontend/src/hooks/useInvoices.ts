import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type {
  InvoiceListResponse,
  InvoiceDetailResponse,
  InvoiceUploadResponse,
  InvoiceConfirmResponse,
  InvoiceConfirmLine,
  InvoicePatchRequest,
} from '../types';

// Re-export for consumers who import from hook
export type {
  InvoiceListItem,
  InvoiceLineResponse,
  InvoiceDetailResponse,
  InvoiceUploadResponse,
  IngredientSuggestion,
} from '../types';

// --- Hooks ---

export function useInvoices(status?: string, search?: string) {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  if (search) params.set('search', search);
  const qs = params.toString();

  return useQuery<InvoiceListResponse>({
    queryKey: ['invoices', status, search],
    staleTime: 60_000, // 1 min
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

  return useMutation<InvoiceDetailResponse, Error, InvoicePatchRequest>({
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
