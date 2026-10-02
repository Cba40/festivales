import { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAppStore } from '../../core/state/store';
import { hasAnyRole, hasPermission } from '../../core/auth/useAuth';

interface ProtectedRouteProps {
  children: ReactNode;
  /** Permiso requerido, formato `module:action`. Basta uno. */
  permission?: string;
  /** Cualquiera de estos roles alcanza. */
  roles?: string[];
  /** Ruta a la que va si no tiene permiso. Por defecto `/dashboard/login`. */
  forbiddenPath?: string;
}

/**
 * Guarda de ruta.
 *
 * Antes solo miraba `isAuthenticated`, que a su vez miraba que hubiera un string
 * en `localStorage`. Ahora hay tres capas:
 *
 * 1. Sin identidad confirmada va al login. No se espera a un 401 para enterarse.
 * 2. Con identidad pero sin el permiso va a la pantalla de acceso denegado, no al
 *    login: redirigirlo al login lo haría pensar que su sesión expiró.
 * 3. Durante la carga no renderiza nada, para no parpadear entre "no autorizado"
 *    y el contenido.
 *
 * Ojo con lo que esto NO hace: el control real está en el backend. Este
 * componente esconde pantallas, no autoriza requests.
 */
export default function ProtectedRoute({
  children,
  permission,
  roles,
  forbiddenPath = '/dashboard/denegado',
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoadingUser, user } = useAppStore((s) => s.auth);

  // Espera a /auth/me antes de decidir. Sin este if, un reload con un token
  // válido se vería como "no autenticado" durante un instante y el usuario sería
  // expulsado al login.
  //
  // `isLoadingUser` arranca en true y lo baja `setUser(...)`, que `useLoadIdentity`
  // llama apenas resuelve (con éxito o con 401). Si no hay token, también.
  if (isLoadingUser) {
    return null;
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/dashboard/login" replace />;
  }

  const faltaPermiso = permission ? !hasPermission(user, permission) : false;
  const faltaRol = roles?.length ? !hasAnyRole(user, ...roles) : false;

  if (faltaPermiso || faltaRol) {
    return <Navigate to={forbiddenPath} replace />;
  }

  return <>{children}</>;
}