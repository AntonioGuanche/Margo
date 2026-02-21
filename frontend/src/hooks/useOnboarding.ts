import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';

export interface ExtractedDish {
  name: string;
  price: number | null;
  category: string | null;
}

interface MenuExtractionResponse {
  dishes: ExtractedDish[];
  image_path: string;
}

interface SuggestedIngredient {
  name: string;
  quantity: number;
  unit: string;
}

export interface DishWithSuggestions {
  name: string;
  price: number | null;
  category: string | null;
  ingredients: SuggestedIngredient[];
}

interface SuggestIngredientsResponse {
  dishes: DishWithSuggestions[];
}

interface OnboardingConfirmDish {
  name: string;
  selling_price: number;
  category: string | null;
  ingredients: SuggestedIngredient[];
}

interface OnboardingConfirmResponse {
  recipes_created: number;
  ingredients_created: number;
}

export function useExtractMenu() {
  return useMutation({
    mutationFn: async (file: File) => {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/onboarding/extract-menu', {
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

      return response.json() as Promise<MenuExtractionResponse>;
    },
  });
}

export function useSuggestIngredients() {
  return useMutation({
    mutationFn: (dishes: ExtractedDish[]) =>
      apiClient<SuggestIngredientsResponse>('/api/onboarding/suggest-ingredients', {
        method: 'POST',
        body: { dishes },
      }),
  });
}

export function useConfirmOnboarding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dishes: OnboardingConfirmDish[]) =>
      apiClient<OnboardingConfirmResponse>('/api/onboarding/confirm', {
        method: 'POST',
        body: { dishes },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['ingredients'] });
    },
  });
}
