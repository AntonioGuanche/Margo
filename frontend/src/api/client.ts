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

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
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

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}
