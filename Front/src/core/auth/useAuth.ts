import { useEffect } from 'react';
import { useAppStore, type AuthUser } from '@/core/state/store';
import { getMe } from '@/services/authService';

/**
 * Autorización en el frontend.
 *
 * `useAuth()` devuelve el actor; `usePermission(code)` dice si puede; `useRole()`
 * lo mismo por rol.
 *
 * Por qué esto NO es una medida de seguridad
 * ------------------------------------------
 * Todo esto corre en el navegador: un operador que abra la consola puede
 * inyectar permisos en el store y ver cualquier menú. Lo único que protege de
 * verdad es el backend, que responde 403.
 *
 * Entonces para qué sirve: para no mostrarle a un contador de campo una pantalla
 * de configuración que va a recibir un 403. La diferencia es de experiencia, no de
 * seguridad, y conviene no confundir las dos cosas.
 */

export function useAuth() {
  const { token, isAuthenticated, user, isLoadingUser } = useAppStore((s) => s.auth);
  return { token, isAuthenticated, user, isLoadingUser };
}

/**
 * Carga la identidad una vez por sesión.
 *
 * Se dispara al montar y no en cada render. Si el token no sirve, `setUser(null)`
 * deja `isAuthenticated` en false y el `ProtectedRoute` redirige al login: antes,
 * con solo mirar `localStorage`, un token expirado se veía como sesión
 * válida hasta que la primera API contestaba 401.
 */
export function useLoadIdentity(): void {
  const token = useAppStore((s) => s.auth.token);
  const isLoadingUser = useAppStore((s) => s.auth.isLoadingUser);
  const isAuthenticated = useAppStore((s) => s.auth.isAuthenticated);

  useEffect(() => {
    // Sin token no hay nada que consultar.
    if (!token) {
      useAppStore.getState().setUser(null);
      return;
    }
    // Ya se consultó (con éxito o con 401): no repetir en cada montaje.
    if (!isLoadingUser || isAuthenticated) return;

    let vivo = true;
    getMe()
      .then((user) => {
        if (vivo) useAppStore.getState().setUser(user);
      })
      .catch(() => {
        // 401 o red caída: en ambos casos no hay identidad confirmada.
        if (vivo) useAppStore.getState().setUser(null);
      });

    return () => {
      vivo = false;
    };
  }, [token, isLoadingUser, isAuthenticated]);
}

/** ¿El actor tiene este permiso? */
export function usePermission(code: string): boolean {
  const user = useAppStore((s) => s.auth.user);
  return hasPermission(user, code);
}

/** ¿El actor tiene alguno de estos roles? */
export function useRole(...codes: string[]): boolean {
  const user = useAppStore((s) => s.auth.user);
  if (!user) return false;
  if (user.is_provider_super_admin || user.is_superuser) return true;
  return codes.some((c) => user.roles.includes(c));
}

/** ¿El actor tiene alguno de estos permisos? */
export function useAnyPermission(...codes: string[]): boolean {
  const user = useAppStore((s) => s.auth.user);
  if (!user) return false;
  if (user.is_provider_super_admin || user.is_superuser) return true;
  return codes.some((c) => user.permissions.includes(c) || user.permissions.includes('*'));
}

// ── Helpers puros ───────────────────────────────────────────────────────────
//
// Fuera de los hooks para poder usarlos desde `ProtectedRoute` (que corre fuera
// de un componente con el store) y testearlos sin React.

export function hasPermission(user: AuthUser | null, code: string): boolean {
  if (!user) return false;
  if (user.is_provider_super_admin || user.is_superuser) return true;
  return user.permissions.includes(code) || user.permissions.includes('*');
}

export function hasAnyRole(user: AuthUser | null, ...codes: string[]): boolean {
  if (!user) return false;
  if (user.is_provider_super_admin || user.is_superuser) return true;
  return codes.some((c) => user.roles.includes(c));
}

/**
 * Filtra una lista por permiso. Para menús y pestañas.
 *
 *   const SECTIONS = [
 *     { key: 'config', label: 'Configuración', permission: 'config:read' },
 *     { key: 'counts', label: 'Conteos', permission: 'counts:write' },
 *   ];
 *   const visibles = filterByPermission(SECTIONS, user);
 */
export function filterByPermission<T extends { permission?: string }>(
  items: T[],
  user: AuthUser | null
): T[] {
  if (!user) return [];
  if (user.is_provider_super_admin || user.is_superuser) return items;
  return items.filter((i) => !i.permission || hasPermission(user, i.permission));
}