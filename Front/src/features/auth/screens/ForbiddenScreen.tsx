import { Link } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import { useAppStore } from '@/core/state/store';
import { Button } from '@/features/dashboard/components/ui/Button';
import { Card } from '@/features/dashboard/components/ui/Card';

/**
 * A dónde cae alguien cuya sesión es válida pero el permiso no alcanza.
 *
 * Existe como pantalla propia y no como redirección al login por dos razones:
 * mandarlo al login lo haría pensar que su sesión expiró y probablemente termine
 * pedir ayuda para algo que es un problema de permisos.
 *
 * La lista de lo que sí puede ver sale de `/auth/me`, que ya está en el store:
 * no se inventan permisos acá.
 */
export function ForbiddenScreen() {
  const user = useAppStore((s) => s.auth.user);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 p-6">
      <Card variant="standard" className="w-full max-w-lg">
        <div className="flex items-start gap-4">
          <ShieldAlert className="w-8 h-8 text-amber-500 shrink-0" aria-hidden />
          <div className="min-w-0">
            <h1 className="text-lg font-bold text-slate-800">
              No tenés permisos para ver esta sección
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              Tu sesión está activa como{' '}
              <span className="font-medium">{user?.username ?? 'usuario'}</span>, pero
              esta pantalla requiere un permiso que no tenés. Si creés que es un
              error, pedile a un administrador municipal que revise tu asignación.
            </p>

            {user && (
              <dl className="mt-4 rounded-lg bg-slate-50 p-3 text-xs">
                <div className="flex gap-2">
                  <dt className="text-slate-500 w-20 shrink-0">Roles</dt>
                  <dd className="text-slate-800">
                    {user.roles.length ? user.roles.join(', ') : '—'}
                  </dd>
                </div>
                <div className="flex gap-2 mt-1">
                  <dt className="text-slate-500 w-20 shrink-0">Alcance</dt>
                  <dd className="text-slate-800">
                    {user.is_global_scope
                      ? 'Todo el evento'
                      : user.scopes
                          .map(
                            (s) =>
                              s.zone_id
                                ? `zona ${s.zone_id.slice(0, 8)}…`
                                : s.event_id
                                  ? `evento ${s.event_id.slice(0, 8)}…`
                                  : 'global'
                          )
                          .join(', ')}
                  </dd>
                </div>
                <div className="flex gap-2 mt-1">
                  <dt className="text-slate-500 w-20 shrink-0">Permisos</dt>
                  <dd className="text-slate-800">{user.permissions.length}</dd>
                </div>
              </dl>
            )}

            <div className="mt-5">
              <Link to="/dashboard">
                <Button variant="primary" size="sm">
                  Volver al dashboard
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

export default ForbiddenScreen;