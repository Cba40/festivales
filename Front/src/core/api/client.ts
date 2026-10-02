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
  // Necesario para que el cookie `HttpOnly` del refresh viaje: sin esto el
  // navegador lo omite en cross-origin y la renovación de sesión no funciona.
  // `credentials: 'include'` es seguro acá justamente porque el cookie es
  // `HttpOnly`: el JavaScript de la página no puede leerlo.
  withCredentials: true,
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
  async (error) => {
    const status = error.response?.status;
    const original = error.config as
      | (typeof error.config & { _retried?: boolean })
      | undefined;

    // ── Refresh transparente ──
    //
    // El access token dura 15 minutos, así que en una sesión larga expira
    // mientras se usa. Antes eso significaba un logout y perder el trabajo en
    // pantalla; ahora se renueva solo.
    //
    // Se reintenta UNA vez (`_retried`): si el refresh falló, el retry también
    // daría 401 y sin ese flag sería un loop infinito de requests.
    if (status === 401 && original && !original._retried) {
      const esPropioRefresh =
        typeof original.url === 'string' && original.url.includes('/auth/refresh');
      const esPropioLogin = typeof original.url === 'string' && original.url.includes('/auth/login');

      if (!esPropioRefresh && !esPropioLogin) {
        original._retried = true;
        try {
          // Sin cuerpo y sin headers de Authorization: el refresh viaja en el
          // cookie HttpOnly y `withCredentials` lo manda solo.
          const { data } = await apiClient.post('/auth/refresh', {});
          useAppStore.getState().login(data.access_token);
          original.headers = { ...original.headers, Authorization: `Bearer ${data.access_token}` };
          return apiClient(original);
        } catch {
          // El refresh no servir (revocado, expirado, cuenta dada de baja):
          // ahora sí se cierra la sesión.
          useAppStore.getState().logout();
          return Promise.reject(error);
        }
      }
    }

    if (status === 401 || status === 403) {
      // 401 = la sesión no sirve más: limpiar. 403 = la sesión sirve pero el
      // permiso no alcanza: NO cerrar sesión, porque expulsar al usuario por
      // falta de permiso lo haría perder lo que estaba haciendo.
      if (status === 401) {
        useAppStore.getState().logout();
      }
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
