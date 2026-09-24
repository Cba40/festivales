import axios from 'axios';
import { useAppStore } from '../state/store';

const API_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD
    ? 'https://festivales-back.vercel.app/api'
    : 'http://localhost:8000/api');

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAppStore.getState().logout();
    }
    return Promise.reject(error);
  },
);

// Origen explícito de una request. NO se aplica globalmente ni como default:
// solo los llamadores que lo eligen agregan el header (prefetch de App.tsx,
// retry user explícito por whitelist). El resto queda sin header => system.
export type RequestOrigin = 'prefetch' | 'user';

export function originHeaders(origin: RequestOrigin): Record<string, string> {
  return { 'X-Request-Origin': origin };
}
