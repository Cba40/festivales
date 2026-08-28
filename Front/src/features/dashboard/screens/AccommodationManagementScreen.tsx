import { useCallback, useEffect, useState } from 'react';
import { isAxiosError } from 'axios';
import { apiClient } from '../../../core/api/client';
import { endpoints } from '../../../core/api/endpoints';

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

const TYPE_BADGES: Record<AccommodationType, string> = {
  hotel: 'bg-blue-100 text-blue-700',
  hostel: 'bg-purple-100 text-purple-700',
  camping: 'bg-green-100 text-green-700',
  other: 'bg-amber-100 text-amber-700',
};

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

  const eliminar = async (a: AccommodationDTO) => {
    const confirmado = window.confirm(
      `¿Desactivar el alojamiento "${a.name}"? Se dejará de mostrar en la app pública. Esta acción no se puede deshacer.`
    );
    if (!confirmado) return;
    try {
      await apiClient.delete(endpoints.accommodationAdmin.delete(eventId, a.id));
      setResult('Alojamiento desactivado.');
      await cargar();
    } catch {
      setError('No se pudo desactivar el alojamiento.');
    }
  };

  const setCampo = <K extends keyof ModalForm>(campo: K, valor: ModalForm[K]) => {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  };

  const inputCls = 'w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500';

  return (
    <div className="space-y-10">
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-slate-700">
            Alojamientos del Evento ({alojamientos.length})
          </h2>
          <button
            onClick={abrirCrear}
            className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md text-sm font-medium transition-colors"
          >
            + Nuevo Alojamiento
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
          <p className="text-sm text-slate-500 italic">Cargando alojamientos...</p>
        ) : alojamientos.length === 0 ? (
          <p className="text-sm text-slate-500 italic text-center py-8 bg-white border border-slate-200 rounded-lg">
            No hay alojamientos registrados. Creá el primero con "+ Nuevo Alojamiento".
          </p>
        ) : (
          <div className="bg-white rounded-lg border border-slate-200 overflow-x-auto">
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
                {alojamientos.map((a) => (
                  <tr key={a.id}>
                    <td className="px-4 py-3 font-medium text-slate-800">{a.name}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${TYPE_BADGES[a.type]}`}
                      >
                        {TYPE_LABELS[a.type]}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{a.address || '—'}</td>
                    <td className="px-4 py-3 text-slate-600">{a.phone || '—'}</td>
                    <td className="px-4 py-3">
                      {a.active ? (
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
                          onClick={() => abrirEditar(a)}
                          className="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md transition-colors"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => void alternarActivo(a)}
                          className="text-sm text-slate-600 hover:bg-slate-100 px-3 py-1.5 rounded-md transition-colors"
                        >
                          {a.active ? 'Desactivar' : 'Activar'}
                        </button>
                        <button
                          onClick={() => void eliminar(a)}
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

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Latitud</label>
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
                <label className="block text-sm font-medium text-slate-700 mb-1">Longitud</label>
                <input
                  type="number"
                  step="0.0001"
                  value={form.longitude}
                  onChange={(e) => setCampo('longitude', e.target.value)}
                  placeholder="-64.0935"
                  className={inputCls}
                />
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
                className="accent-emerald-600"
              />
              Activo (visible en la pantalla "Hospedajes")
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
    </div>
  );
}
