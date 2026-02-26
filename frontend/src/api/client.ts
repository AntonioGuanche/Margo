const API_BASE = '';

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown;
};

export async function apiClient<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<T> {
  const token = localStorage.getItem('token');

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) ?? {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    // Network error (offline, DNS failure, etc.)
    throw new Error('Pas de connexion internet. Vérifie ton réseau et réessaie.');
  }

  if (response.status === 401) {
    const wasAuthenticated = !!localStorage.getItem('token');
    localStorage.removeItem('token');

    if (wasAuthenticated) {
      // Session expired — dispatch event so Layout can show a modal
      window.dispatchEvent(new CustomEvent('session-expired'));
    } else {
      window.location.href = '/login';
    }

    throw new Error('Session expirée — reconnecte-toi pour continuer.');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: undefined }));
    const fallbackMessages: Record<number, string> = {
      400: 'Données invalides',
      403: 'Action non autorisée',
      404: 'Ressource introuvable',
      409: 'Conflit — cet élément existe déjà',
      413: 'Fichier trop volumineux',
      415: 'Format de fichier non supporté',
      422: 'Données invalides',
      429: 'Trop de requêtes — réessaie dans quelques secondes',
      500: 'Oups, quelque chose a mal tourné. Réessaie.',
      502: 'Service IA temporairement indisponible',
    };
    const message = error.detail ?? fallbackMessages[response.status] ?? 'Erreur serveur';
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}
