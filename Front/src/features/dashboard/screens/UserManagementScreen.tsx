import { useCallback, useEffect, useState } from 'react';
import { Pencil, Plus, UserX, Users } from 'lucide-react';

import {
  ASSIGNABLE_ROLES,
  ROLE_LABELS,
  createUser,
  deactivateUser,
  errorMessage,
  listUsers,
  updateUser,
  type UserDTO,
} from '@/services/userAdminService';
import { useAppStore } from '@/core/state/store';
import { Badge } from '@/features/dashboard/components/ui/Badge';
import { Card } from '@/features/dashboard/components/ui/Card';
import { Button } from '@/features/dashboard/components/ui/Button';
import { ConfirmDialog } from '@/features/dashboard/components/ui/ConfirmDialog';
import { DashboardHeader } from '@/features/dashboard/components/DashboardHeader';
import { AppFooter } from '@/components/AppFooter';

const MIN_PASSWORD = 8;

interface FormState {
  username: string;
  password: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

const EMPTY: FormState = {
  username: '',
  password: '',
  email: '',
  full_name: '',
  role: ASSIGNABLE_ROLES[0],
  is_active: true,
};

/**
 * Gestión de usuarios del administrador municipal.
 *
 * Dos decisiones que conviene que se noten al leer:
 *
 * **La UI replica las reglas del servidor, pero no las aplica.** El backend impide
 * que alguien se desactive a sí mismo o se quite su propio rol, y devuelve 409 con
 * un mensaje que explica por qué. Acá los botones se ocultan en ese caso para no
 * ofrecer algo que va a fallar, pero la validación real es la del servidor: un
 * cliente alternativo o un `curl` la saltearían igual. Por eso el 409 se muestra
 * tal cual.
 *
 * **El password solo se envía al crear o al cambiarlo.** En el modal de edición el
 * campo arranca vacío y, si queda vacío, no se manda nada en el PUT: mandar una
 * contraseña vacía o un placeholder le cambiaría la clave al usuario sin que lo
 * pidiera.
 */
export function UserManagementScreen() {
  const usernameActual = useAppStore((s) => s.auth.user?.username ?? '');

  const [users, setUsers] = useState<UserDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mostrarInactivos, setMostrarInactivos] = useState(false);

  const [modalAbierto, setModalAbierto] = useState(false);
  const [editando, setEditando] = useState<UserDTO | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [guardando, setGuardando] = useState(false);
  const [errorForm, setErrorForm] = useState<string | null>(null);

  const [porDesactivar, setPorDesactivar] = useState<UserDTO | null>(null);
  const [procesando, setProcesando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const data = await listUsers(mostrarInactivos);
      setUsers(data.users);
      setError(null);
    } catch (err) {
      setError(errorMessage(err, 'No se pudo cargar la lista de usuarios.'));
    } finally {
      setLoading(false);
    }
  }, [mostrarInactivos]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const abrirNuevo = () => {
    setEditando(null);
    setForm(EMPTY);
    setErrorForm(null);
    setModalAbierto(true);
  };

  const abrirEdicion = (u: UserDTO) => {
    setEditando(u);
    setForm({
      // El password arranca vacío y NO se precarga: el backend nunca lo devuelve,
      // así que no hay nada que mostrar, y mandar el placeholder en el PUT le
      // cambiaría la clave al usuario.
      username: u.username,
      password: '',
      email: u.email ?? '',
      full_name: u.full_name ?? '',
      role: u.roles[0]?.role_code ?? ASSIGNABLE_ROLES[0],
      is_active: u.is_active,
    });
    setErrorForm(null);
    setModalAbierto(true);
  };

  const guardar = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorForm(null);

    if (!editando) {
      if (form.username.trim().length < 3) {
        setErrorForm('El usuario debe tener al menos 3 caracteres.');
        return;
      }
      if (form.password.length < MIN_PASSWORD) {
        setErrorForm(`La contraseña debe tener al menos ${MIN_PASSWORD} caracteres.`);
        return;
      }
    } else if (form.password && form.password.length < MIN_PASSWORD) {
      setErrorForm(`La contraseña debe tener al menos ${MIN_PASSWORD} caracteres.`);
      return;
    }

    setGuardando(true);
    try {
      if (editando) {
        // Solo se manda `password` si el operador lo escribió. Mandarlo siempre
        // (aunque sea vacío) dejaría al usuario con una contraseña que no eligió.
        await updateUser(editando.id, {
          email: form.email.trim() || null,
          full_name: form.full_name.trim() || null,
          is_active: form.is_active,
          ...(form.password ? { password: form.password } : {}),
        });
      } else {
        await createUser({
          username: form.username.trim(),
          password: form.password,
          email: form.email.trim() || null,
          full_name: form.full_name.trim() || null,
          role: form.role,
        });
      }
      setModalAbierto(false);
      await cargar();
    } catch (err) {
      setErrorForm(errorMessage(err, 'No se pudo guardar el usuario.'));
    } finally {
      setGuardando(false);
    }
  };

  const confirmarDesactivar = async () => {
    if (!porDesactivar) return;
    setProcesando(true);
    try {
      await deactivateUser(porDesactivar.id);
      setPorDesactivar(null);
      await cargar();
    } catch (err) {
      setError(errorMessage(err, 'No se pudo desactivar el usuario.'));
      setPorDesactivar(null);
    } finally {
      setProcesando(false);
    }
  };

  const esYo = (u: UserDTO) => u.username === usernameActual;

  return (
    <div className="min-h-screen bg-slate-50 w-full flex flex-col">
      <DashboardHeader
        title="Gestión de Usuarios"
        subtitle="Altas, edición y roles"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={mostrarInactivos}
                onChange={(e) => setMostrarInactivos(e.target.checked)}
                className="rounded"
              />
              Mostrar inactivos
            </label>
            <Button variant="primary" size="sm" onClick={abrirNuevo}>
              <Plus className="w-4 h-4 mr-1" />
              Nuevo usuario
            </Button>
          </div>
        }
      />

      <main className="flex-1 p-4 sm:p-6">
        {error && (
          <div className="p-3 mb-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        <Card variant="standard">
          {loading ? (
            <p className="text-sm text-slate-400 italic">Cargando usuarios…</p>
          ) : users.length === 0 ? (
            <p className="text-sm text-slate-400 italic">
              No hay usuarios para mostrar.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500 border-b">
                    <th className="py-2 pr-4 font-medium">Usuario</th>
                    <th className="py-2 pr-4 font-medium">Email</th>
                    <th className="py-2 pr-4 font-medium">Roles</th>
                    <th className="py-2 pr-4 font-medium">Estado</th>
                    <th className="py-2 font-medium text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b last:border-0">
                      <td className="py-2 pr-4">
                        <span className="font-medium text-slate-800">
                          {u.username}
                        </span>
                        {u.full_name && (
                          <span className="block text-xs text-slate-500">
                            {u.full_name}
                          </span>
                        )}
                        {esYo(u) && (
                          <span className="text-xs text-indigo-600"> (vos)</span>
                        )}
                      </td>
                      <td className="py-2 pr-4 text-slate-600">
                        {u.email ?? '—'}
                      </td>
                      <td className="py-2 pr-4">
                        <div className="flex flex-wrap gap-1">
                          {u.roles.length === 0 ? (
                            <span className="text-xs text-slate-400">—</span>
                          ) : (
                            u.roles.map((r) => (
                              <Badge key={r.role_id} variant="neutral">
                                {ROLE_LABELS[r.role_code] ?? r.role_code}
                              </Badge>
                            ))
                          )}
                        </div>
                      </td>
                      <td className="py-2 pr-4">
                        {!u.is_active ? (
                          <Badge variant="error">Inactivo</Badge>
                        ) : u.locked_until ? (
                          <Badge variant="warning">Bloqueado</Badge>
                        ) : (
                          <Badge variant="success">Activo</Badge>
                        )}
                      </td>
                      <td className="py-2">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => abrirEdicion(u)}
                            aria-label={`Editar ${u.username}`}
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          {/* No se ofrece algo que el servidor va a rechazar:
                              desactivarse a sí mismo deja al municipio sin
                              nadie con users:write. */}
                          {!esYo(u) && u.is_active && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setPorDesactivar(u)}
                              aria-label={`Desactivar ${u.username}`}
                            >
                              <UserX className="w-4 h-4 text-red-600" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </main>

      <AppFooter />

      {modalAbierto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <Card variant="standard" className="w-full max-w-md">
            <div className="flex items-center gap-2 mb-4">
              <Users className="w-5 h-5 text-indigo-600" />
              <h2 className="text-lg font-bold text-slate-800">
                {editando ? `Editar ${editando.username}` : 'Nuevo usuario'}
              </h2>
            </div>

            {errorForm && (
              <div className="p-2 mb-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                {errorForm}
              </div>
            )}

            <form onSubmit={guardar} className="space-y-3">
              <label className="block text-sm">
                <span className="text-slate-700 font-medium">Usuario</span>
                <input
                  type="text"
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  disabled={editando !== null || guardando}
                  required
                />
                {editando && (
                  <span className="text-xs text-slate-500">
                    El usuario no se cambia una vez creado.
                  </span>
                )}
              </label>

              <label className="block text-sm">
                <span className="text-slate-700 font-medium">
                  {editando ? 'Nueva contraseña (opcional)' : 'Contraseña'}
                </span>
                <input
                  type="password"
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder={editando ? 'Dejala vacía para no cambiarla' : ''}
                  autoComplete="new-password"
                  disabled={guardando}
                  required={editando === null}
                />
              </label>

              <label className="block text-sm">
                <span className="text-slate-700 font-medium">Email (opcional)</span>
                <input
                  type="email"
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  disabled={guardando}
                />
              </label>

              <label className="block text-sm">
                <span className="text-slate-700 font-medium">
                  Nombre completo (opcional)
                </span>
                <input
                  type="text"
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg"
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  disabled={guardando}
                />
              </label>

              {!editando && (
                <label className="block text-sm">
                  <span className="text-slate-700 font-medium">Rol</span>
                  <select
                    className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg"
                    value={form.role}
                    onChange={(e) => setForm({ ...form, role: e.target.value })}
                    disabled={guardando}
                  >
                    {ASSIGNABLE_ROLES.map((r) => (
                      <option key={r} value={r}>
                        {ROLE_LABELS[r] ?? r}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              {editando && (
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    // La UI lo oculta, pero el checkbox también se deshabilita
                    // para el usuario que se está editando a sí mismo: el 409 del
                    // servidor es la garantía real, esto solo evita la frustration
                    // de escribir algo que va a ser rechazado.
                    disabled={esYo(editando)}
                    onChange={(e) =>
                      setForm({ ...form, is_active: e.target.checked })
                    }
                  />
                  <span className="text-slate-700">Activo</span>
                </label>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setModalAbierto(false)}
                  disabled={guardando}
                >
                  Cancelar
                </Button>
                <Button type="submit" variant="primary" size="sm" disabled={guardando}>
                  {guardando ? 'Guardando…' : 'Guardar'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      <ConfirmDialog
        open={porDesactivar !== null}
        title="Desactivar usuario"
        message={
          porDesactivar
            ? `Se desactivará a "${porDesactivar.username}". No podrá entrar al sistema, pero la cuenta y su historial se conservan.`
            : ''
        }
        onCancel={() => setPorDesactivar(null)}
        onConfirm={() => void confirmarDesactivar()}
        confirmLabel={procesando ? 'Desactivando…' : 'Desactivar'}
      />
    </div>
  );
}

export default UserManagementScreen;