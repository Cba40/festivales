import { useCallback, useEffect, useState } from 'react';
import { isAxiosError } from 'axios';
import { Settings, Plus, Pencil, Trash2, MapPin, ChevronUp, ChevronDown } from 'lucide-react';
import { AdminMapSelector } from '../../../components/AdminMapSelector';
import {
  getCities,
  getEmergencies,
  createEmergency,
  createCity,
  updateEmergency,
  deleteEmergency,
  type CityDTO,
  type EmergencyAdminDTO,
} from '../../../services/emergencyAdmin';
import { EMERGENCY_TYPE_LABELS, type EmergencyType } from '../constants/emergencyLabels';
import { Badge, type BadgeVariant } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';

type ModalState =
  | { mode: 'create' }
  | { mode: 'edit'; emergencia: EmergencyAdminDTO }
  | null;

interface CityModalForm {
  name: string;
  province: string;
  country: string;
}

const emptyCityForm: CityModalForm = {
  name: '',
  province: 'Córdoba',
  country: 'Argentina',
};

const EMERGENCY_TYPE_BADGE_VARIANTS: Record<EmergencyType, BadgeVariant> = {
  policia: 'info',
  bomberos: 'error',
  salud: 'success',
  defensa_civil: 'warning',
  numero_emergencia: 'error',
  otro: 'neutral',
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

  const [cityModalOpen, setCityModalOpen] = useState(false);
  const [cityForm, setCityForm] = useState<CityModalForm>(emptyCityForm);
  const [citySaving, setCitySaving] = useState(false);
  const [cityError, setCityError] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  const ciudadSeleccionada = cities.find((c) => c.id === cityId);

  const cargarCiudades = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getCities();
      setCities(data || []);
      if (data && data.length > 0) {
        setCityId((prev) => (prev && data.some((c) => c.id === prev) ? prev : data[0].id));
      } else {
        setCityId('');
      }
      setError(null);
    } catch {
      setError('No se pudieron cargar las ciudades. Verifica la conexión.');
      setCityId('');
    } finally {
      setLoading(false);
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

  const abrirCrearCiudad = () => {
    setCityForm(emptyCityForm);
    setCityError(null);
    setCityModalOpen(true);
  };

  const guardarCiudad = async () => {
    const name = cityForm.name.trim();
    if (!name) {
      setCityError('El nombre de la ciudad es obligatorio.');
      return;
    }
    setCitySaving(true);
    setCityError(null);
    try {
      const nueva = await createCity({
        name,
        province: cityForm.province.trim() || null,
        country: cityForm.country.trim() || 'Argentina',
      });
      await cargarCiudades();
      setCityId(nueva.id);
      setCityModalOpen(false);
      setResult(`Ciudad "${nueva.name}" creada.`);
    } catch (err) {
      const status = isAxiosError(err) ? err.response?.status : undefined;
      if (status === 409) {
        setCityError('Ya existe una ciudad con ese nombre y provincia.');
      } else {
        setCityError('No se pudo crear la ciudad.');
      }
    } finally {
      setCitySaving(false);
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
    try {
      await deleteEmergency(e.id);
      setResult('Punto de emergencia desactivado.');
      await cargar();
    } catch {
      setError('No se pudo desactivar el punto de emergencia.');
    }
  };

  const handleDeleteConfirm = async () => {
    if (!pendingDeleteId) return;
    const e = emergencies.find((em) => em.id === pendingDeleteId);
    if (!e) return;
    await eliminar(e);
    setPendingDeleteId(null);
  };

  const setCampo = <K extends keyof ModalForm>(campo: K, valor: ModalForm[K]) => {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  };

  const inputCls = 'w-full border-slate-300 rounded-md py-2 px-3 focus:ring-indigo-500 focus:border-indigo-500';

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
              {cities.length === 0 && <option value="">Sin ciudades configuradas</option>}
              {cities.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} {c.province ? `(${c.province})` : ''}
                </option>
              ))}
            </select>
            <button
              onClick={abrirCrearCiudad}
              className="text-sm text-slate-600 hover:bg-slate-100 border border-slate-200 rounded-md py-1.5 px-3 transition-colors inline-flex items-center gap-1.5"
            >
              <Settings className="w-4 h-4" />
              Gestionar / Crear Ciudad
            </button>
          </div>
          <Button variant="primary" onClick={abrirCrear}>
            <Plus className="w-4 h-4" />
            Nuevo Punto de Emergencia
          </Button>
        </div>

        {result && (
          <p className="mb-4 text-sm text-green-700 bg-green-50 border border-green-200 rounded-md p-3">
            {result}
          </p>
        )}

        {loading ? (
          <p className="text-sm text-slate-500 italic">Cargando ciudades y emergencias...</p>
        ) : error ? (
          <div className="mb-4 flex items-center justify-between gap-3 p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
            <span>{error}</span>
            <button
              type="button"
              onClick={() => {
                void cargarCiudades();
                void cargar();
              }}
              className="whitespace-nowrap underline font-medium"
            >
              Reintentar
            </button>
          </div>
        ) : !cityId || cities.length === 0 ? (
          <div className="text-center text-slate-500 py-8 bg-white border border-slate-200 rounded-lg">
            <p className="text-sm">No hay ciudades configuradas en el sistema.</p>
            <p className="text-xs mt-2">Usa el botón "Gestionar / Crear Ciudad" para agregar una.</p>
          </div>
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
                      <Badge variant={EMERGENCY_TYPE_BADGE_VARIANTS[e.type]}>
                        {EMERGENCY_TYPE_LABELS[e.type]}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {e.emergency_number || e.phone || '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{ciudadSeleccionada?.name || '—'}</td>
                    <td className="px-4 py-3">
                      {e.active ? (
                        <Badge variant="success">Activo</Badge>
                      ) : (
                        <Badge variant="neutral">Inactivo</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => abrirEditar(e)}
                          title="Editar"
                          className="mr-1"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                          Editar
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => void alternarActivo(e)}
                          title={e.active ? 'Desactivar' : 'Activar'}
                        >
                          {e.active ? 'Desactivar' : 'Activar'}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setPendingDeleteId(e.id)}
                          title="Eliminar"
                          className="text-red-600 hover:bg-red-50"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          Eliminar
                        </Button>
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
          <Card
            variant="standard"
            className="w-full max-w-2xl mx-4 space-y-4 max-h-[90vh] overflow-y-auto"
          >
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
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setMapPickerOpen(true)}
                    >
                      <MapPin className="w-4 h-4" />
                      Seleccionar en mapa
                    </Button>

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

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowManualCoords((v) => !v)}
                    className="mt-2"
                  >
                    {showManualCoords ? (
                      <><ChevronUp className="w-4 h-4" /> Ocultar edición manual</>
                    ) : (
                      <><ChevronDown className="w-4 h-4" /> Edición manual avanzada</>
                    )}
                  </Button>

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
                className="accent-indigo-600"
              />
              Activo (visible en la pantalla "Emergencias")
            </label>

            {modalError && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
                {modalError}
              </p>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" onClick={() => setModal(null)}>
                Cancelar
              </Button>
              <Button
                variant="primary"
                onClick={() => void guardar()}
                disabled={modalSaving}
              >
                {modalSaving ? 'Guardando...' : 'Guardar'}
              </Button>
            </div>
          </Card>
        </div>
      )}

      {cityModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50">
          <Card variant="standard" className="w-full max-w-sm mx-4 space-y-4">
            <h3 className="text-lg font-semibold text-slate-800">Crear Ciudad</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nombre de la ciudad *</label>
                <input
                  type="text"
                  value={cityForm.name}
                  onChange={(e) => setCityForm((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="Ej: Jesús María"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Provincia</label>
                <input
                  type="text"
                  value={cityForm.province}
                  onChange={(e) => setCityForm((prev) => ({ ...prev, province: e.target.value }))}
                  placeholder="Córdoba"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">País</label>
                <input
                  type="text"
                  value={cityForm.country}
                  onChange={(e) => setCityForm((prev) => ({ ...prev, country: e.target.value }))}
                  placeholder="Argentina"
                  className={inputCls}
                />
              </div>
            </div>

            {cityError && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
                {cityError}
              </p>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" onClick={() => setCityModalOpen(false)}>
                Cancelar
              </Button>
              <Button
                variant="primary"
                onClick={() => void guardarCiudad()}
                disabled={citySaving}
              >
                {citySaving ? 'Guardando...' : 'Guardar'}
              </Button>
            </div>
          </Card>
        </div>
      )}

      {mapPickerOpen && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-[60]">
          <Card
            variant="standard"
            className="w-full max-w-2xl mx-4 space-y-4 max-h-[90vh] overflow-y-auto"
          >
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
              <Button
                variant="secondary"
                onClick={() => {
                  setCampo('latitude', '');
                  setCampo('longitude', '');
                  setMapPickerOpen(false);
                }}
              >
                Limpiar y cerrar
              </Button>
              <Button variant="primary" onClick={() => setMapPickerOpen(false)}>
                Confirmar ubicación
              </Button>
            </div>
          </Card>
        </div>
      )}

      <ConfirmDialog
        open={pendingDeleteId !== null}
        title="Eliminar punto de emergencia"
        message={`¿Desactivar el punto de emergencia "${emergencies.find((e) => e.id === pendingDeleteId)?.name ?? ''}"? Se dejará de mostrar en la app pública. Esta acción no se puede deshacer.`}
        confirmLabel="Eliminar"
        cancelLabel="Cancelar"
        variant="destructive"
        onConfirm={() => void handleDeleteConfirm()}
        onCancel={() => setPendingDeleteId(null)}
      />
    </div>
  );
}
