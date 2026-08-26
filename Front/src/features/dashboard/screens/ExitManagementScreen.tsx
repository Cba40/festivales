import { useCallback, useEffect, useState } from 'react';
import { isAxiosError } from 'axios';
import { apiClient } from '../../../core/api/client';
import { endpoints } from '../../../core/api/endpoints';

interface ExitDestinationDTO {
  id: string;
  event_id: string;
  name: string;
  active: boolean;
}

interface SalidaZoneDTO {
  id: string;
  name: string;
}

type ModalState =
  | { mode: 'create' }
  | { mode: 'edit'; destino: ExitDestinationDTO }
  | null;

type ZoneSaveStatus = 'idle' | 'saving' | 'saved' | 'error';

export function ExitManagementScreen({ eventId }: { eventId: string }) {
  const [destinos, setDestinos] = useState<ExitDestinationDTO[]>([]);
  const [destinosLoading, setDestinosLoading] = useState(true);
  const [destinosError, setDestinosError] = useState<string | null>(null);

  const [modal, setModal] = useState<ModalState>(null);
  const [modalName, setModalName] = useState('');
  const [modalActive, setModalActive] = useState(true);
  const [modalSaving, setModalSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const [zonas, setZonas] = useState<SalidaZoneDTO[]>([]);
  const [zonasLoading, setZonasLoading] = useState(true);
  const [asignaciones, setAsignaciones] = useState<Record<string, string[]>>({});
  const [statusPorZona, setStatusPorZona] = useState<Record<string, ZoneSaveStatus>>({});

  const cargarDestinos = useCallback(async () => {
    try {
      const res = await apiClient.get<ExitDestinationDTO[]>(
        endpoints.exitAdmin.destinations.list(eventId)
      );
      setDestinos(res.data);
      setDestinosError(null);
    } catch {
      setDestinosError('No se pudieron cargar los destinos.');
    } finally {
      setDestinosLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    let vigente = true;

    const cargarZonasYAsignaciones = async () => {
      try {
        const res = await apiClient.get<{ id: string; name: string; type: string }[]>(
          endpoints.zones.list(eventId)
        );
        if (!vigente) return;
        const salidas = res.data
          .filter((z) => z.type === 'salida')
          .map((z) => ({ id: z.id, name: z.name }));
        setZonas(salidas);

        const resultados = await Promise.all(
          salidas.map(async (zona) => {
            try {
              const r = await apiClient.get<{ destination_ids: string[] }>(
                endpoints.exitAdmin.zoneDestinations.get(eventId, zona.id)
              );
              return [zona.id, r.data.destination_ids] as const;
            } catch {
              return [zona.id, [] as string[]] as const;
            }
          })
        );
        if (!vigente) return;
        setAsignaciones(Object.fromEntries(resultados));
      } catch {
        if (vigente) setDestinosError('No se pudieron cargar las zonas de salida.');
      } finally {
        if (vigente) setZonasLoading(false);
      }
    };

    void cargarZonasYAsignaciones();
    return () => {
      vigente = false;
    };
  }, [eventId]);

  useEffect(() => {
    void cargarDestinos();
  }, [cargarDestinos]);

  const abrirCrear = () => {
    setModalName('');
    setModalActive(true);
    setModalError(null);
    setModal({ mode: 'create' });
  };

  const abrirEditar = (destino: ExitDestinationDTO) => {
    setModalName(destino.name);
    setModalActive(destino.active);
    setModalError(null);
    setModal({ mode: 'edit', destino });
  };

  const guardarModal = async () => {
    const nombre = modalName.trim();
    if (!nombre) {
      setModalError('El nombre es obligatorio.');
      return;
    }
    setModalSaving(true);
    setModalError(null);
    try {
      if (modal?.mode === 'edit') {
        await apiClient.put(endpoints.exitAdmin.destinations.update(eventId, modal.destino.id), {
          name: nombre,
          active: modalActive,
        });
      } else {
        await apiClient.post(endpoints.exitAdmin.destinations.create(eventId), {
          name: nombre,
          active: modalActive,
        });
      }
      setModal(null);
      await cargarDestinos();
    } catch (err) {
      const status = isAxiosError(err) ? err.response?.status : undefined;
      if (status === 409) {
        setModalError('Ya existe un destino con ese nombre en este evento.');
      } else {
        setModalError('No se pudo guardar el destino.');
      }
    } finally {
      setModalSaving(false);
    }
  };

  const alternarActivo = async (destino: ExitDestinationDTO) => {
    try {
      await apiClient.put(endpoints.exitAdmin.destinations.update(eventId, destino.id), {
        active: !destino.active,
      });
      await cargarDestinos();
    } catch {
      setDestinosError('No se pudo actualizar el estado del destino.');
    }
  };

  const eliminarDestino = async (destino: ExitDestinationDTO) => {
    const confirmado = window.confirm(
      `¿Eliminar el destino "${destino.name}"? También se quitará de todas las salidas que lo tienen asignado. Esta acción no se puede deshacer.`
    );
    if (!confirmado) return;
    try {
      await apiClient.delete(endpoints.exitAdmin.destinations.delete(eventId, destino.id));
      await cargarDestinos();
    } catch {
      setDestinosError('No se pudo eliminar el destino.');
    }
  };

  const toggleDestinoEnZona = async (zonaId: string, destinoId: string) => {
    const actuales = asignaciones[zonaId] ?? [];
    const nuevos = actuales.includes(destinoId)
      ? actuales.filter((id) => id !== destinoId)
      : [...actuales, destinoId];

    setAsignaciones((prev) => ({ ...prev, [zonaId]: nuevos }));
    setStatusPorZona((prev) => ({ ...prev, [zonaId]: 'saving' }));

    try {
      await apiClient.put(endpoints.exitAdmin.zoneDestinations.update(eventId, zonaId), {
        destination_ids: nuevos,
      });
      setStatusPorZona((prev) => ({ ...prev, [zonaId]: 'saved' }));
    } catch {
      setAsignaciones((prev) => ({ ...prev, [zonaId]: actuales }));
      setStatusPorZona((prev) => ({ ...prev, [zonaId]: 'error' }));
    }
  };

  return (
    <div className="space-y-10">
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-slate-700">
            Destinos del Evento ({destinos.length})
          </h2>
          <button
            onClick={abrirCrear}
            className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md text-sm font-medium transition-colors"
          >
            + Nuevo Destino
          </button>
        </div>

        {destinosError && (
          <p className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
            {destinosError}
          </p>
        )}

        {destinosLoading ? (
          <p className="text-sm text-slate-500 italic">Cargando destinos...</p>
        ) : destinos.length === 0 ? (
          <p className="text-sm text-slate-500 italic text-center py-8 bg-white border border-slate-200 rounded-lg">
            No hay destinos registrados. Creá el primero con "+ Nuevo Destino".
          </p>
        ) : (
          <div className="bg-white rounded-lg border border-slate-200 divide-y divide-slate-100">
            {destinos.map((destino) => (
              <div key={destino.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <span className="font-medium text-slate-800">{destino.name}</span>
                  {!destino.active && (
                    <span className="ml-2 text-xs text-slate-500">(desactivado)</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => abrirEditar(destino)}
                    className="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md transition-colors"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => void alternarActivo(destino)}
                    className="text-sm text-slate-600 hover:bg-slate-100 px-3 py-1.5 rounded-md transition-colors"
                  >
                    {destino.active ? 'Desactivar' : 'Activar'}
                  </button>
                  <button
                    onClick={() => void eliminarDestino(destino)}
                    className="text-sm text-red-600 hover:bg-red-50 px-3 py-1.5 rounded-md transition-colors"
                  >
                    Eliminar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-700 mb-1">
          Destinos por Zona de Salida
        </h2>
        <p className="text-sm text-slate-500 mb-4">
          Marcá qué destinos están disponibles desde cada zona de salida. Los cambios se guardan
          automáticamente.
        </p>

        {zonasLoading ? (
          <p className="text-sm text-slate-500 italic">Cargando zonas de salida...</p>
        ) : zonas.length === 0 ? (
          <p className="text-sm text-slate-500 italic text-center py-8 bg-white border border-slate-200 rounded-lg">
            No hay zonas tipo "salida" registradas. Creálas desde la solapa "Zonas".
          </p>
        ) : (
          <div className="space-y-3">
            {zonas.map((zona) => {
              const seleccionados = asignaciones[zona.id] ?? [];
              const estado = statusPorZona[zona.id] ?? 'idle';
              return (
                <div
                  key={zona.id}
                  className="bg-white p-4 rounded-lg border border-slate-200"
                >
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="font-semibold text-slate-800">{zona.name}</h3>
                    {estado === 'saving' && (
                      <span className="text-xs text-slate-500">Guardando...</span>
                    )}
                    {estado === 'saved' && (
                      <span className="text-xs text-emerald-600">Guardado</span>
                    )}
                    {estado === 'error' && (
                      <span className="text-xs text-red-600">Error al guardar</span>
                    )}
                  </div>
                  {destinos.length === 0 ? (
                    <p className="text-sm text-slate-500 italic">
                      No hay destinos disponibles para asignar.
                    </p>
                  ) : (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {destinos.map((destino) => (
                        <label
                          key={destino.id}
                          className={`flex items-center gap-2 text-sm px-3 py-2 rounded-md border cursor-pointer select-none ${
                            seleccionados.includes(destino.id)
                              ? 'border-emerald-300 bg-emerald-50 text-slate-800'
                              : 'border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={seleccionados.includes(destino.id)}
                            onChange={() => void toggleDestinoEnZona(zona.id, destino.id)}
                            className="accent-emerald-600"
                          />
                          <span>
                            {destino.name}
                            {!destino.active && (
                              <span className="ml-1 text-xs text-slate-400">(desactivado)</span>
                            )}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {modal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 mx-4 space-y-4">
            <h3 className="text-lg font-semibold text-slate-800">
              {modal.mode === 'create' ? 'Nuevo Destino' : `Editar Destino`}
            </h3>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nombre</label>
              <input
                type="text"
                value={modalName}
                onChange={(e) => setModalName(e.target.value)}
                placeholder="Ej: Córdoba"
                className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={modalActive}
                onChange={(e) => setModalActive(e.target.checked)}
                className="accent-emerald-600"
              />
              Activo (visible en la pantalla "Salir")
            </label>
            {modalError && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
                {modalError}
              </p>
            )}
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setModal(null)}
                className="py-2 px-4 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => void guardarModal()}
                disabled={modalSaving}
                className="py-2 px-4 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md transition-colors"
              >
                {modalSaving ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
