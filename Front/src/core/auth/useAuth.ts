import { useEffect } from 'react';
import { useAppStore, type AuthUser } from '@/core/state/store';
import { getMe } from '@/services/authService';

/**
 * Autorización en el frontend.
 *
 * `useAuth()` devuelve el actor; `usePermission(code)` dice si puede; `useRole()`
 * lo mismo por rol. Para RESTRINGIR por rol sin que el bypass del super admin se
 * aplique al super admin, usar `useExactRole()`.
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

/**
 * ¿El actor tiene alguno de estos roles?
 *
 * Ojo con lo que responde para un super admin: devuelve `true` SIEMPRE, para
 * cualquier código. Pregunta "¿puede actuar como?", no "¿qué rol tiene?". Para una
 * guarda de ruta (`ProtectedRoute roles=[...]`) eso es lo correcto.
 */
export function useRole(...codes: string[]): boolean {
  const user = useAppStore((s) => s.auth.user);
  if (!user) return false;
  if (user.is_provider_super_admin || user.is_superuser) return true;
  return codes.some((c) => user.roles.includes(c));
}

/**
 * ¿El rol del actor es alguno de estos? SIN el bypass del super admin.
 *
 * Hace falta para RESTRINGIR, y no para autorizar. "Los operadores de campo solo
 * ven estas tres acciones" tiene que leer la lista de roles tal cual: si la
 * pregunta pasa por `useRole`, el super admin contesta `true` para
 * 'OPERADOR_CAMPO' sin serlo, la restricción le cae encima y le oculta justamente
 * lo que debería ver más: las pestañas de predicciones y analytics del motor y el
 * botón de "Motor y Análisis".
 *
 * `useRole` para lo que el actor PUEDE hacer; `useExactRole` para lo que le
 * corresponde por el rol que tiene.
 */
export function useExactRole(...codes: string[]): boolean {
  const user = useAppStore((s) => s.auth.user);
  return hasExactRole(user, ...codes);
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

/** Pareja sin bypass de `hasAnyRole`. Ver `useExactRole`. */
export function hasExactRole(user: AuthUser | null, ...codes: string[]): boolean {
  if (!user) return false;
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