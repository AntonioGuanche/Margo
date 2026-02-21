import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api/client';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface LoginResponse {
  message: string;
}

interface VerifyResponse {
  access_token: string;
  token_type: string;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
  });

  useEffect(() => {
    const token = localStorage.getItem('token');
    setState({ isAuthenticated: !!token, isLoading: false });
  }, []);

  const login = useCallback(async (email: string) => {
    const data = await apiClient<LoginResponse>('/auth/login', {
      method: 'POST',
      body: { email },
    });
    return data;
  }, []);

  const verify = useCallback(async (token: string) => {
    const data = await apiClient<VerifyResponse>('/auth/verify', {
      method: 'POST',
      body: { token },
    });
    localStorage.setItem('token', data.access_token);
    setState({ isAuthenticated: true, isLoading: false });
    return data;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    setState({ isAuthenticated: false, isLoading: false });
  }, []);

  return { ...state, login, verify, logout };
}
