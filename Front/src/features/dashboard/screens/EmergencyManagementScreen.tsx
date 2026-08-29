import { useCallback, useEffect, useState } from 'react';
import { isAxiosError } from 'axios';
import { AdminMapSelector } from '../../../components/AdminMapSelector';
import {
  getCities,
  getEmergencies,
  createEmergency,
  updateEmergency,
  deleteEmergency,
  type CityDTO,
  type EmergencyAdminDTO,
  type EmergencyType,
} from '../../../services/emergencyAdmin';

type ModalState =
  | { mode: 'create' }
  | { mode: 'edit'; emergencia: EmergencyAdminDTO }
  | null;

const TYPE_LABELS: Record<EmergencyType, string> = {
  policia: 'Policía',
  bomberos: 'Bomberos',
  salud: 'Salud',
  defensa_civil: 'Defensa Civil',
  numero_emergencia: 'Número de Emergencia',
  otro: 'Otro',
};

const TYPE_BADGES: Record<EmergencyType, string> = {
  policia: 'bg-blue-100 text-blue-700',
  bomberos: 'bg-red-100 text-red-700',
  salud: 'bg-green-100 text-green-700',
  defensa_civil: 'bg-amber-100 text-amber-700',
  numero_emergencia: 'bg-rose-100 text-rose-700',
  otro: 'bg-slate-100 text-slate-700',
};

interface ModalForm {
  name: string;
  type: EmergencyType;
  phone: string;
  emergency_number: string;
  address: string;
  reference: string;
  latitude: string;
  longitude: string;
  services: string;
  schedule: string;
  active: boolean;
}

const emptyForm: ModalForm = {
  name: '',
  type: 'policia',
  phone: '',
  emergency_number: '',
  address: '',
  reference: '',
  latitude: '',
  longitude: '',
  services: '',
  schedule: '24hs',
  active: true,
};

export function EmergencyManagementScreen() {
  const [cities, setCities] = useState<CityDTO[]>([]);
  const [cityId, setCityId] = useState<string>('');

  const [emergencies, setEmergencies] = useState<EmergencyAdminDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const [modal, setModal] = useState<ModalState>(null);
  const [form, setForm] = useState<ModalForm>(emptyForm);
  const [modalSaving, setModalSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [mapPickerOpen, setMapPickerOpen] = useState(false);
  const [showManualCoords, setShowManualCoords] = useState(false);

  const ciudadSeleccionada = cities.find((c) => c.id === cityId);

  const cargarCiudades = useCallback(async () => {
    try {
      const data = await getCities();
      setCities(data);
      if (data.length > 0) {
        setCityId((prev) => (prev && data.some((c) => c.id === prev) ? prev : data[0].id));
      }
      setError(null);
    } catch {
      setError('No se pudieron cargar las ciudades.');
    }
  }, []);

  const cargar = useCallback(async () => {
    if (!cityId) return;
    try {
      const data = await getEmergencies(cityId, true);
      setEmergencies(data);
      setError(null);
    } catch {
      setError('No se pudieron cargar los puntos de emergencia.');
    } finally {
      setLoading(false);
    }
  }, [cityId]);

  useEffect(() => {
    void cargarCiudades();
  }, [cargarCiudades]);

  useEffect(() => {
    // Solo recargamos cuando hay ciudad seleccionada (evita el primer render vacío).
    if (cityId) {
      setLoading(true);
      void cargar();
    }
  }, [cityId, cargar]);

  const abrirCrear = () => {
    setForm({ ...emptyForm, type: 'policia' });
    setModalError(null);
    setShowManualCoords(false);
    setModal({ mode: 'create' });
  };

  const abrirEditar = (e: EmergencyAdminDTO) => {
    setForm({
      name: e.name,
      type: e.type,
      phone: e.phone ?? '',
      emergency_number: e.emergency_number ?? '',
      address: e.address ?? '',
      reference: e.reference ?? '',
      latitude: e.latitude != null ? String(e.latitude) : '',
      longitude: e.longitude != null ? String(e.longitude) : '',
      services: e.services ?? '',
      schedule: e.schedule ?? '',
      active: e.active,
    });
    setModalError(null);
    setShowManualCoords(false);
    setModal({ mode: 'edit', emergencia: e });
  };

  const numeroOpcional = (value: string): number | null => {
    if (value === '') return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  };

  const esNumeroEmergencia = form.type === 'numero_emergencia';

  const guardar = async () => {
    const name = form.name.trim();
    if (!name) {
      setModalError('El nombre es obligatorio.');
      return;
    }
    if (!cityId) {
      setModalError('Seleccioná una ciudad para el punto de emergencia.');
      return;
    }
    setModalSaving(true);
    setModalError(null);
    try {
      const payload = {
        city_id: cityId,
        name,
        type: form.type,
        phone: form.phone.trim() || null,
        emergency_number: form.emergency_number.trim() || null,
        address: form.address.trim() || null,
        reference: form.reference.trim() || null,
        latitude: numeroOpcional(form.latitude),
        longitude: numeroOpcional(form.longitude),
        services: form.services.trim() || null,
        schedule: form.schedule.trim() || null,
        active: form.active,
      };
      if (modal?.mode === 'edit') {
        await updateEmergency(modal.emergencia.id, payload);
      } else {
        await createEmergency(payload);
      }
      setModal(null);
      setResult(modal?.mode === 'edit' ? 'Punto de emergencia actualizado.' : 'Punto de emergencia creado.');
      await cargar();
    } catch (err) {
      const status = isAxiosError(err) ? err.response?.status : undefined;
      if (status === 409) {
        setModalError('Ya existe un punto de emergencia con ese nombre en esta ciudad.');
      } else {
        setModalError('No se pudo guardar el punto de emergencia.');
      }
    } finally {
      setModalSaving(false);
    }
  };

  const alternarActivo = async (e: EmergencyAdminDTO) => {
    try {
      await updateEmergency(e.id, { active: !e.active });
      setResult(e.active ? 'Punto de emergencia desactivado.' : 'Punto de emergencia activado.');
      await cargar();
    } catch {
      setError('No se pudo actualizar el estado del punto de emergencia.');
    }
  };

  const eliminar = async (e: EmergencyAdminDTO) => {
    const confirmado = window.confirm(
      `¿Desactivar el punto de emergencia "${e.name}"? Se dejará de mostrar en la app pública. Esta acción no se puede deshacer.`
    );
    if (!confirmado) return;
    try {
      await deleteEmergency(e.id);
      setResult('Punto de emergencia desactivado.');
      await cargar();
    } catch {
      setError('No se pudo desactivar el punto de emergencia.');
    }
  };

  const setCampo = <K extends keyof ModalForm>(campo: K, valor: ModalForm[K]) => {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  };

  const inputCls = 'w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500';

  return (
    <div className="space-y-10">
      <section>
        <div className="flex justify-between items-center mb-4 gap-3">
          <div className="flex items-center gap-3 flex-wrap">
            <h2 className="text-lg font-semibold text-slate-700">
              Puntos de Emergencia ({emergencies.length})
            </h2>
            <select
              value={cityId}
              onChange={(e) => setCityId(e.target.value)}
              className="border-slate-300 rounded-md py-1.5 px-3 text-sm"
            >
              {cities.length === 0 && <option value="">Cargando ciudades...</option>}
              {cities.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} {c.province ? `(${c.province})` : ''}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={abrirCrear}
            className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md text-sm font-medium transition-colors"
          >
            + Nuevo Punto de Emergencia
          </button>
        </div>

        {error && (
          <p className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
            {error}
          </p>
        )}
        {result && (
          <p className="mb-4 text-sm text-green-700 bg-green-50 border border-green-200 rounded-md p-3">
            {result}
          </p>
        )}

        {loading ? (
          <p className="text-sm text-slate-500 italic">Cargando emergencias...</p>
        ) : !cityId ? (
          <p className="text-sm text-slate-500 italic text-center py-8 bg-white border border-slate-200 rounded-lg">
            No hay ciudades disponibles. Creá una ciudad en el backend o los seeds.
          </p>
        ) : emergencies.length === 0 ? (
          <p className="text-sm text-slate-500 italic text-center py-8 bg-white border border-slate-200 rounded-lg">
            No hay puntos de emergencia en esta ciudad. Creá el primero con "+ Nuevo Punto de Emergencia".
          </p>
        ) : (
          <div className="bg-white rounded-lg border border-slate-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="px-4 py-3 font-medium">Nombre</th>
                  <th className="px-4 py-3 font-medium">Tipo</th>
                  <th className="px-4 py-3 font-medium">Contacto</th>
                  <th className="px-4 py-3 font-medium">Ciudad</th>
                  <th className="px-4 py-3 font-medium">Estado</th>
                  <th className="px-4 py-3 font-medium text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {emergencies.map((e) => (
                  <tr key={e.id}>
                    <td className="px-4 py-3 font-medium text-slate-800">{e.name}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${TYPE_BADGES[e.type]}`}
                      >
                        {TYPE_LABELS[e.type]}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {e.emergency_number || e.phone || '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{ciudadSeleccionada?.name || '—'}</td>
                    <td className="px-4 py-3">
                      {e.active ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">
                          Activo
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-200 text-slate-600">
                          Inactivo
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1">
                        <button
                          onClick={() => abrirEditar(e)}
                          className="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md transition-colors"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => void alternarActivo(e)}
                          className="text-sm text-slate-600 hover:bg-slate-100 px-3 py-1.5 rounded-md transition-colors"
                        >
                          {e.active ? 'Desactivar' : 'Activar'}
                        </button>
                        <button
                          onClick={() => void eliminar(e)}
                          className="text-sm text-red-600 hover:bg-red-50 px-3 py-1.5 rounded-md transition-colors"
                        >
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {modal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6 mx-4 space-y-4 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-slate-800">
              {modal.mode === 'create' ? 'Nuevo Punto de Emergencia' : 'Editar Punto de Emergencia'}
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setCampo('name', e.target.value)}
                  placeholder="Ej: Cuartel Bomberos Voluntarios"
                  className={inputCls}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Tipo</label>
                <select
                  value={form.type}
                  onChange={(e) => setCampo('type', e.target.value as EmergencyType)}
                  className={inputCls}
                >
                  <option value="policia">Policía</option>
                  <option value="bomberos">Bomberos</option>
                  <option value="salud">Salud</option>
                  <option value="defensa_civil">Defensa Civil</option>
                  <option value="numero_emergencia">Número de Emergencia</option>
                  <option value="otro">Otro</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Teléfono de contacto</label>
                <input
                  type="text"
                  value={form.phone}
                  onChange={(e) => setCampo('phone', e.target.value)}
                  placeholder="+54 3525 420100"
                  className={inputCls}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Número de emergencia</label>
                <input
                  type="text"
                  value={form.emergency_number}
                  onChange={(e) => setCampo('emergency_number', e.target.value)}
                  placeholder="911, 107, 100"
                  className={inputCls}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Servicios que brinda</label>
                <input
                  type="text"
                  value={form.services}
                  onChange={(e) => setCampo('services', e.target.value)}
                  placeholder="Incendios, rescates, prevención"
                  className={inputCls}
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Dirección</label>
                <input
                  type="text"
                  value={form.address}
                  onChange={(e) => setCampo('address', e.target.value)}
                  placeholder="Calle Los Bomberos 450"
                  className={inputCls}
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Referencia</label>
                <input
                  type="text"
                  value={form.reference}
                  onChange={(e) => setCampo('reference', e.target.value)}
                  placeholder="A 300m de la plaza"
                  className={inputCls}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Horario</label>
                <input
                  type="text"
                  value={form.schedule}
                  onChange={(e) => setCampo('schedule', e.target.value)}
                  placeholder="24hs"
                  className={inputCls}
                />
              </div>

              {!esNumeroEmergencia && (
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Ubicación (coordenadas)
                  </label>

                  <p className="text-xs text-slate-500 mb-2">
                    Los números de emergencia (911, 107) no requieren ubicación. Para el resto de
                    tipos definí las coordenadas del punto.
                  </p>

                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setMapPickerOpen(true)}
                      className="py-2 px-4 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded-md transition-colors"
                    >
                      📍 Seleccionar en mapa
                    </button>

                    {form.latitude !== '' || form.longitude !== '' ? (
                      <>
                        <span className="text-sm text-slate-600 font-mono">
                          {form.latitude || '—'}, {form.longitude || '—'}
                        </span>
                        <button
                          type="button"
                          onClick={() => {
                            setCampo('latitude', '');
                            setCampo('longitude', '');
                          }}
                          className="text-sm font-medium text-slate-500 hover:text-slate-700 hover:bg-slate-100 px-2 py-1 rounded-md transition-colors"
                        >
                          Limpiar
                        </button>
                      </>
                    ) : (
                      <span className="text-sm text-slate-400">Sin coordenadas definidas</span>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={() => setShowManualCoords((v) => !v)}
                    className="mt-2 text-xs font-medium text-blue-600 hover:underline"
                  >
                    {showManualCoords ? '▲ Ocultar edición manual' : '▼ Edición manual avanzada'}
                  </button>

                  {showManualCoords && (
                    <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-slate-500 mb-1">Latitud</label>
                        <input
                          type="number"
                          step="0.0001"
                          value={form.latitude}
                          onChange={(e) => setCampo('latitude', e.target.value)}
                          placeholder="-30.9801"
                          className={inputCls}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-500 mb-1">Longitud</label>
                        <input
                          type="number"
                          step="0.0001"
                          value={form.longitude}
                          onChange={(e) => setCampo('longitude', e.target.value)}
                          placeholder="-64.0935"
                          className={inputCls}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {esNumeroEmergencia && (
                <div className="sm:col-span-2">
                  <p className="text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded-md p-3">
                    Tipo "Número de Emergencia": no requiere ubicación geográfica. Se mostrará
                    destacado en el bloque de emergencias críticas.
                  </p>
                </div>
              )}
            </div>

            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={form.active}
                onChange={(e) => setCampo('active', e.target.checked)}
                className="accent-emerald-600"
              />
              Activo (visible en la pantalla "Emergencias")
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
                onClick={() => void guardar()}
                disabled={modalSaving}
                className="py-2 px-4 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md transition-colors"
              >
                {modalSaving ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {mapPickerOpen && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-[60]">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6 mx-4 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold text-slate-800">Seleccionar ubicación</h3>
              <button
                type="button"
                onClick={() => setMapPickerOpen(false)}
                className="text-slate-500 hover:text-slate-700 text-2xl leading-none"
                aria-label="Cerrar"
              >
                ×
              </button>
            </div>

            <AdminMapSelector
              lat={form.latitude !== '' ? Number(form.latitude) : undefined}
              lng={form.longitude !== '' ? Number(form.longitude) : undefined}
              onChangeLocation={(newLat, newLng) => {
                setCampo('latitude', String(newLat));
                setCampo('longitude', String(newLng));
              }}
            />

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setCampo('latitude', '');
                  setCampo('longitude', '');
                  setMapPickerOpen(false);
                }}
                className="py-2 px-4 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
              >
                Limpiar y cerrar
              </button>
              <button
                type="button"
                onClick={() => setMapPickerOpen(false)}
                className="py-2 px-4 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded-md transition-colors"
              >
                Confirmar ubicación
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
