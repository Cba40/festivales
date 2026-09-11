import { useCallback, useEffect, useMemo, useState } from 'react';
import { isAxiosError } from 'axios';
import { Plus, Pencil, Trash2, MapPin, ChevronUp, ChevronDown, Search, X, Building2, Home, Tent } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { apiClient } from '../../../core/api/client';
import { endpoints } from '../../../core/api/endpoints';
import { AdminMapSelector } from '../../../components/AdminMapSelector';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge, type BadgeVariant } from '../components/ui/Badge';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { RefreshButton } from '../components/ui';

type AccommodationType = 'hotel' | 'hostel' | 'camping' | 'other';

interface AccommodationDTO {
  id: string;
  event_id: string;
  name: string;
  type: AccommodationType;
  address: string | null;
  reference: string | null;
  latitude: number | null;
  longitude: number | null;
  phone: string | null;
  website: string | null;
  official_info_url: string | null;
  active: boolean;
}

type ModalState =
  | { mode: 'create' }
  | { mode: 'edit'; alojamiento: AccommodationDTO }
  | null;

const TYPE_LABELS: Record<AccommodationType, string> = {
  hotel: 'Hotel',
  hostel: 'Hostel',
  camping: 'Camping',
  other: 'Otros',
};

const TYPE_BADGE_VARIANTS: Record<AccommodationType, BadgeVariant> = {
  hotel: 'info',
  hostel: 'neutral',
  camping: 'success',
  other: 'warning',
};

const TYPE_GROUP_LABELS: Record<string, string> = {
  hotel: 'Hoteles',
  hostel: 'Hostels',
  camping: 'Campings',
  other: 'Otros',
};

const TYPE_ICONS: Record<string, LucideIcon> = {
  hotel: Building2,
  hostel: Home,
  camping: Tent,
  other: MapPin,
};

function normalizeText(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

interface ModalForm {
  name: string;
  type: AccommodationType;
  address: string;
  reference: string;
  latitude: string;
  longitude: string;
  phone: string;
  website: string;
  official_info_url: string;
  active: boolean;
}

const emptyForm: ModalForm = {
  name: '',
  type: 'hotel',
  address: '',
  reference: '',
  latitude: '',
  longitude: '',
  phone: '',
  website: '',
  official_info_url: '',
  active: true,
};

export function AccommodationManagementScreen({ eventId }: { eventId: string }) {
  const [alojamientos, setAlojamientos] = useState<AccommodationDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const [modal, setModal] = useState<ModalState>(null);
  const [form, setForm] = useState<ModalForm>(emptyForm);
  const [modalSaving, setModalSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [mapPickerOpen, setMapPickerOpen] = useState(false);
  const [showManualCoords, setShowManualCoords] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const res = await apiClient.get<AccommodationDTO[]>(
        endpoints.accommodationAdmin.list(eventId)
      );
      setAlojamientos(res.data);
      setError(null);
    } catch {
      setError('No se pudieron cargar los alojamientos.');
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await cargar();
    } finally {
      setRefreshing(false);
    }
  };

  const filteredAndGrouped = useMemo(() => {
    const term = normalizeText(searchTerm.trim());
    const filtered = term
      ? alojamientos.filter((a) => {
          const haystack = normalizeText(`${a.name} ${a.type} ${a.address ?? ''}`);
          return haystack.includes(term);
        })
      : alojamientos;

    const grouped = new Map<string, AccommodationDTO[]>();
    for (const alojamiento of filtered) {
      const list = grouped.get(alojamiento.type) ?? [];
      list.push(alojamiento);
      grouped.set(alojamiento.type, list);
    }

    return Array.from(grouped.entries())
      .map(([type, groupAccommodations]) => ({
        type,
        accommodations: groupAccommodations.sort((a, b) => a.name.localeCompare(b.name, 'es')),
      }))
      .sort((a, b) =>
        (TYPE_GROUP_LABELS[a.type] ?? a.type).localeCompare(TYPE_GROUP_LABELS[b.type] ?? b.type, 'es')
      );
  }, [alojamientos, searchTerm]);

  const abrirCrear = () => {
    setForm(emptyForm);
    setModalError(null);
    setModal({ mode: 'create' });
  };

  const abrirEditar = (a: AccommodationDTO) => {
    setForm({
      name: a.name,
      type: a.type,
      address: a.address ?? '',
      reference: a.reference ?? '',
      latitude: a.latitude != null ? String(a.latitude) : '',
      longitude: a.longitude != null ? String(a.longitude) : '',
      phone: a.phone ?? '',
      website: a.website ?? '',
      official_info_url: a.official_info_url ?? '',
      active: a.active,
    });
    setModalError(null);
    setModal({ mode: 'edit', alojamiento: a });
  };

  const numeroOpcional = (value: string): number | null => {
    if (value === '') return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  };

  const guardar = async () => {
    const name = form.name.trim();
    if (!name) {
      setModalError('El nombre es obligatorio.');
      return;
    }
    setModalSaving(true);
    setModalError(null);
    try {
      const payload = {
        name,
        type: form.type,
        address: form.address.trim() || null,
        reference: form.reference.trim() || null,
        latitude: numeroOpcional(form.latitude),
        longitude: numeroOpcional(form.longitude),
        phone: form.phone.trim() || null,
        website: form.website.trim() || null,
        official_info_url: form.official_info_url.trim() || null,
        active: form.active,
      };
      if (modal?.mode === 'edit') {
        await apiClient.put(
          endpoints.accommodationAdmin.update(eventId, modal.alojamiento.id),
          payload
        );
      } else {
        await apiClient.post(endpoints.accommodationAdmin.create(eventId), payload);
      }
      setModal(null);
      setResult(modal?.mode === 'edit' ? 'Alojamiento actualizado.' : 'Alojamiento creado.');
      await cargar();
    } catch (err) {
      const status = isAxiosError(err) ? err.response?.status : undefined;
      if (status === 409) {
        setModalError('Ya existe un alojamiento con ese nombre en este evento.');
      } else {
        setModalError('No se pudo guardar el alojamiento.');
      }
    } finally {
      setModalSaving(false);
    }
  };

  const alternarActivo = async (a: AccommodationDTO) => {
    try {
      await apiClient.put(endpoints.accommodationAdmin.update(eventId, a.id), {
        active: !a.active,
      });
      setResult(a.active ? 'Alojamiento desactivado.' : 'Alojamiento activado.');
      await cargar();
    } catch {
      setError('No se pudo actualizar el estado del alojamiento.');
    }
  };

  const handleDeleteConfirm = async () => {
    if (!pendingDeleteId) return;
    try {
      await apiClient.delete(endpoints.accommodationAdmin.delete(eventId, pendingDeleteId));
      setResult('Alojamiento desactivado.');
      await cargar();
    } catch {
      setError('No se pudo desactivar el alojamiento.');
    } finally {
      setPendingDeleteId(null);
    }
  };

  const setCampo = <K extends keyof ModalForm>(campo: K, valor: ModalForm[K]) => {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  };

  const inputCls = 'w-full border-slate-300 rounded-md py-2 px-3 focus:ring-indigo-500 focus:border-indigo-500';

  return (
    <div className="space-y-10">
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-slate-700">
            Alojamientos del Evento ({alojamientos.length})
          </h2>
          <div className="flex items-center gap-2">
            <RefreshButton onClick={() => void handleRefresh()} loading={refreshing} />
            <Button variant="primary" onClick={abrirCrear}>
              <Plus className="w-4 h-4" />
              Nuevo Alojamiento
            </Button>
          </div>
        </div>

        <Card variant="standard">
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
            <p className="text-sm text-slate-500 italic text-center py-8">Cargando alojamientos...</p>
          ) : alojamientos.length === 0 ? (
            <p className="text-sm text-slate-500 italic text-center py-8">
              No hay alojamientos registrados. Creá el primero con "+ Nuevo Alojamiento".
            </p>
          ) : (
            <>
              <div className="relative mb-4">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Buscar alojamiento por nombre, tipo o ubicación..."
                  className="w-full pl-9 pr-9 py-2 text-sm rounded-lg border border-slate-300 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                />
                {searchTerm.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setSearchTerm('')}
                    title="Limpiar búsqueda"
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 text-slate-400 hover:text-slate-600 rounded-full"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {filteredAndGrouped.length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-8">
                  No se encontraron alojamientos que coincidan con '{searchTerm.trim()}'.
                </p>
              ) : (
                <div className="space-y-6">
                  {filteredAndGrouped.map((group) => {
                    const Icon = TYPE_ICONS[group.type] ?? MapPin;
                    const label = TYPE_GROUP_LABELS[group.type] ?? group.type;
                    return (
                      <section key={group.type}>
                        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-2">
                          <Icon className="w-4 h-4 text-indigo-600" />
                          {label}
                          <span className="text-xs font-normal text-slate-400">
                            {group.accommodations.length === 1 ? '(1 alojamiento)' : `(${group.accommodations.length} alojamientos)`}
                          </span>
                        </h3>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-slate-200 text-left text-slate-500">
                                <th className="px-4 py-3 font-medium">Nombre</th>
                                <th className="px-4 py-3 font-medium">Tipo</th>
                                <th className="px-4 py-3 font-medium">Dirección</th>
                                <th className="px-4 py-3 font-medium">Teléfono</th>
                                <th className="px-4 py-3 font-medium">Estado</th>
                                <th className="px-4 py-3 font-medium text-right">Acciones</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {group.accommodations.map((a) => (
                                <tr key={a.id}>
                                  <td className="px-4 py-3 font-medium text-slate-800">{a.name}</td>
                                  <td className="px-4 py-3">
                                    <Badge variant={TYPE_BADGE_VARIANTS[a.type]}>{TYPE_LABELS[a.type]}</Badge>
                                  </td>
                                  <td className="px-4 py-3 text-slate-600">{a.address || '—'}</td>
                                  <td className="px-4 py-3 text-slate-600">{a.phone || '—'}</td>
                                  <td className="px-4 py-3">
                                    {a.active ? (
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
                                        onClick={() => abrirEditar(a)}
                                        title="Editar"
                                        className="mr-1"
                                      >
                                        <Pencil className="w-3.5 h-3.5" />
                                        Editar
                                      </Button>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => void alternarActivo(a)}
                                        title={a.active ? 'Desactivar' : 'Activar'}
                                      >
                                        {a.active ? 'Desactivar' : 'Activar'}
                                      </Button>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setPendingDeleteId(a.id)}
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
                      </section>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </Card>
      </section>

      <ConfirmDialog
        open={pendingDeleteId !== null}
        title="Eliminar alojamiento"
        message={`¿Desactivar el alojamiento "${alojamientos.find((a) => a.id === pendingDeleteId)?.name ?? ''}"? Se dejará de mostrar en la app pública. Esta acción no se puede deshacer.`}
        confirmLabel="Eliminar"
        cancelLabel="Cancelar"
        variant="destructive"
        onConfirm={() => void handleDeleteConfirm()}
        onCancel={() => setPendingDeleteId(null)}
      />

      {modal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50">
          <Card
            variant="standard"
            className="w-full max-w-2xl mx-4 space-y-4 max-h-[90vh] overflow-y-auto"
          >
            <h3 className="text-lg font-semibold text-slate-800">
              {modal.mode === 'create' ? 'Nuevo Alojamiento' : 'Editar Alojamiento'}
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setCampo('name', e.target.value)}
                  placeholder="Ej: Hotel de la Estación"
                  className={inputCls}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Tipo</label>
                <select
                  value={form.type}
                  onChange={(e) => setCampo('type', e.target.value as AccommodationType)}
                  className={inputCls}
                >
                  <option value="hotel">Hotel</option>
                  <option value="hostel">Hostel</option>
                  <option value="camping">Camping</option>
                  <option value="other">Otros</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Teléfono</label>
                <input
                  type="text"
                  value={form.phone}
                  onChange={(e) => setCampo('phone', e.target.value)}
                  placeholder="+54 3525 420-101"
                  className={inputCls}
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Dirección</label>
                <input
                  type="text"
                  value={form.address}
                  onChange={(e) => setCampo('address', e.target.value)}
                  placeholder="Av. Independencia 1250, Jesús María, Córdoba"
                  className={inputCls}
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Referencia</label>
                <input
                  type="text"
                  value={form.reference}
                  onChange={(e) => setCampo('reference', e.target.value)}
                  placeholder="A 1,2 km del anfiteatro"
                  className={inputCls}
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Ubicación (coordenadas)
                </label>

                <div className="flex flex-wrap items-center gap-3">
                  <Button variant="primary" onClick={() => setMapPickerOpen(true)}>
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
                  className="mt-2 text-xs text-indigo-600"
                >
                  {showManualCoords ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  {showManualCoords ? 'Ocultar edición manual' : 'Edición manual avanzada'}
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
                        placeholder="-30.9815"
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

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Sitio Web</label>
                <input
                  type="url"
                  value={form.website}
                  onChange={(e) => setCampo('website', e.target.value)}
                  placeholder="https://hoteldelaestacion.com.ar"
                  className={inputCls}
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">URL Info Oficial</label>
                <input
                  type="url"
                  value={form.official_info_url}
                  onChange={(e) => setCampo('official_info_url', e.target.value)}
                  placeholder="https://jesusmaria.gob.ar/turismo"
                  className={inputCls}
                />
              </div>
            </div>

            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={form.active}
                onChange={(e) => setCampo('active', e.target.checked)}
                className="accent-indigo-600"
              />
              Activo (visible en la pantalla "Hospedajes")
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
              <Button variant="primary" onClick={() => void guardar()} disabled={modalSaving}>
                {modalSaving ? 'Guardando...' : 'Guardar'}
              </Button>
            </div>
          </Card>
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
          </div>
        </div>
      )}
    </div>
  );
}
