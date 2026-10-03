import { apiClient } from '@/core/api/client';

/**
 * Servicio de gestión de usuarios del administrador municipal.
 *
 * El `password` solo viaja en `createUser` y `changePassword`. Ninguna respuesta
 * lo trae, y `UserDTO` no tiene un campo para eso a propósito: si el backend
 * alguna vez lo devolviera, el tipo lo delataría en el typecheck en vez de
 * colarse en la UI.
 */
export interface UserRoleDTO {
  role_id: string;
  role_code: string;
  role_name: string;
  event_id: string | null;
  zone_id: string | null;
  granted_at: string;
}

export interface UserDTO {
  id: string;
  username: string;
  email: string | null;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  locked_until: string | null;
  last_login_at: string | null;
  created_at: string;
  roles: UserRoleDTO[];
}

export interface UserListDTO {
  total: number;
  users: UserDTO[];
}

export interface UserCreateDTO {
  username: string;
  password: string;
  email?: string | null;
  full_name?: string | null;
  role: string;
}

export interface UserUpdateDTO {
  password?: string | null;
  email?: string | null;
  full_name?: string | null;
  is_active?: boolean | null;
}

export interface RoleAssignDTO {
  role_code: string;
  event_id?: string | null;
  zone_id?: string | null;
}

/** Roles que se pueden asignar. `SUPER_ADMIN` no: no existe en `users`. */
export const ASSIGNABLE_ROLES = [
  'MUNICIPAL_ADMIN',
  'OPERADOR_CAMPO',
  'ANALISTA',
] as const;

export const ROLE_LABELS: Record<string, string> = {
  SUPER_ADMIN: 'Super Administrador (proveedor)',
  MUNICIPAL_ADMIN: 'Administrador Municipal',
  OPERADOR_CAMPO: 'Operador de Campo',
  ANALISTA: 'Analista',
};

export async function listUsers(
  includeInactive = false
): Promise<UserListDTO> {
  const { data } = await apiClient.get<UserListDTO>('/admin/users', {
    params: { include_inactive: includeInactive },
  });
  return data;
}

export async function createUser(body: UserCreateDTO): Promise<UserDTO> {
  const { data } = await apiClient.post<UserDTO>('/admin/users', body);
  return data;
}

export async function updateUser(
  id: string,
  body: UserUpdateDTO
): Promise<UserDTO> {
  const { data } = await apiClient.put<UserDTO>(`/admin/users/${id}`, body);
  return data;
}

export async function deactivateUser(id: string): Promise<UserDTO> {
  const { data } = await apiClient.delete<UserDTO>(`/admin/users/${id}`);
  return data;
}

export async function assignRole(
  id: string,
  body: RoleAssignDTO
): Promise<UserDTO> {
  const { data } = await apiClient.post<UserDTO>(`/admin/users/${id}/roles`, body);
  return data;
}

export async function removeRole(
  id: string,
  roleId: string
): Promise<void> {
  await apiClient.delete(`/admin/users/${id}/roles/${roleId}`);
}

// ── Errores del dominio ─────────────────────────────────────────────────────
//
// El backend responde en español con mensajes pensados para el operador
// (explican por qué no puede desactivarse a sí mismo, cuál es su alcance, etc.).
// Esos mensajes se muestran tal cual: el backend los escribió para eso.

export function errorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data
      ?.detail;
    if (typeof detail === 'string') return detail;
    // FastAPI devuelve una lista de errores de validación en ese endpoint.
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string; loc?: string[] };
      const campo = first.loc?.filter((p) => p !== 'body').join('.');
      return campo ? `${campo}: ${first.msg}` : (first.msg ?? fallback);
    }
  }
  return fallback;
}