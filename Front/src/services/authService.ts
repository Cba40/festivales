import { apiClient } from '@/core/api/client';
import type { AuthUser } from '@/core/state/store';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_expires_in: number;
  refresh_token: string;
  username: string;
  roles: string[];
  permissions: string[];
}

export interface MeResponse extends AuthUser {}

/**
 * Login. El access token va al store (y a `localStorage`, ver la nota de
 * seguridad en `client.ts`) y el refresh queda en un cookie `HttpOnly` que el
 * backend pone solo: esta función ni lo lee ni lo manda.
 */
export async function login(
  username: string,
  password: string
): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>('/auth/login', {
    username,
    password,
  });
  return data;
}

/** Identidad y capacidades del actor. Es la fuente de los permisos de la UI. */
export async function getMe(): Promise<MeResponse> {
  const { data } = await apiClient.get<MeResponse>('/auth/me');
  return data;
}

/**
 * Renueva la sesión.
 *
 * El refresh viaja en el cookie `HttpOnly` que el backend pone solo, así que acá no se
 * manda nada: `withCredentials` hace que el navegador lo adjunte solo. Si el
 * refresh fue revocado (logout, cambio de contraseña) esto falla con 401 y es el
 * interceptor quien limpia la sesión.
 */
export async function refreshSession(): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>('/auth/refresh', {}, {
    headers: { 'X-Request-Origin': 'refresh' },
  });
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout', {});
}

export async function changePassword(
  currentPassword: string,
  newPassword: string
): Promise<void> {
  await apiClient.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

// ── Tokens de error de auth ─────────────────────────────────────────────────
//
// El backend responde en español y el operador lo lee. Estos códigos son para
// código, no para mostrar.

export const AUTH_ERRORS = {
  invalidCredentials: 'Credenciales inválidas',
  locked: 'Cuenta bloqueada',
} as const;