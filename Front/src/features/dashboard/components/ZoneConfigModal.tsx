import { useState, useEffect } from 'react';
import { useZoneConfigMutations } from '../hooks/useZoneConfigMutations';
import { useZoneTypes } from '../hooks/useZoneBehaviors';
import { useZoneSubtypes } from '../hooks/useZoneSubtypes';
import { fetchDefaultServiceConfig } from '../hooks/useServiceConfigs';
import { useServiceConfigMutations } from '../hooks/useServiceConfigMutations';
import type { Zone } from '../types';
import { DEFAULTS_POR_SUBTIPO, ZONE_TYPES } from '../constants';
import { AdminMapSelector } from '../../../components/AdminMapSelector';

interface Props {
  zone: Zone;
  onClose: () => void;
}

export function ZoneConfigModal({ zone, onClose }: Props) {
  const { updateZone, patchZoneFields, loading } = useZoneConfigMutations();
  const { create: createConfig, update: updateConfig } =
    useServiceConfigMutations();
  const { zoneTypes } = useZoneTypes();
  const [name, setName] = useState(zone.name);
  const [type, setType] = useState(zone.type);
  const [capacity, setCapacity] = useState(String(zone.capacity));
  const [lat, setLat] = useState(zone.lat !== undefined ? String(zone.lat) : '');
  const [lng, setLng] = useState(zone.lng !== undefined ? String(zone.lng) : '');
  const [subtipo, setSubtipo] = useState(zone.subtipo || '');
  const [permanencia, setPermanencia] = useState('');
  const [serviceError, setServiceError] = useState<string | null>(null);

  // slug → id del catálogo zone_types para consultar los subtipos del tipo actual.
  const selectedTypeRow = zoneTypes.find((t) => t.slug === type) ?? null;
  const zoneTypeId = selectedTypeRow?.id ?? null;
  const {
    data: subtipos,
    isLoading: subtiposLoading,
    error: subtiposError,
  } = useZoneSubtypes(zoneTypeId);

  const showSubtipoField =
    zoneTypeId !== null &&
    (subtipos.length > 0 || subtiposLoading || subtiposError !== null || subtipo !== '');

  useEffect(() => {
    setName(zone.name);
    setType(zone.type);
    setCapacity(String(zone.capacity));
    setLat(zone.lat !== undefined ? String(zone.lat) : '');
    setLng(zone.lng !== undefined ? String(zone.lng) : '');
    setSubtipo(zone.subtipo || '');
    setServiceError(null);
  }, [zone]);

  // Precarga la permanencia del subtipo: config default existente en
  // service_configs o el default sugerido si aún no hay fila.
  useEffect(() => {
    let cancelled = false;
    if (!zoneTypeId || !subtipo) {
      setPermanencia('');
      return;
    }
    const load = async () => {
      try {
        const config = await fetchDefaultServiceConfig(zoneTypeId, subtipo);
        if (!cancelled) {
          setPermanencia(
            config
              ? String(config.average_duration_min)
              : String(DEFAULTS_POR_SUBTIPO[subtipo] ?? '')
          );
        }
      } catch (err) {
        console.error('[ZoneConfigModal] lookup service_config falló:', err);
        if (!cancelled) {
          setPermanencia(String(DEFAULTS_POR_SUBTIPO[subtipo] ?? ''));
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [zoneTypeId, subtipo]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !capacity || Number(capacity) <= 0) return;

    // 1) Campos base vía PUT /config (name/type/capacity/coords).
    await updateZone(zone.id, {
      name: name.trim(),
      type,
      capacity: Number(capacity),
      lat: lat ? Number(lat) : undefined,
      lng: lng ? Number(lng) : undefined,
    });

    // 2) Subtipo: PUT /config no lo acepta → PATCH /zones/{id}.
    if ((zone.subtipo || '') !== subtipo) {
      const okSubtipo = await patchZoneFields(zone.id, {
        subtipo: subtipo === '' ? null : subtipo,
      });
      if (!okSubtipo) {
        console.error('[ZoneConfigModal] persistir subtipo falló');
        setServiceError('La zona se actualizó, pero no se pudo guardar el subtipo.');
        return;
      }
    }

    // 3) Sincronizar service_configs (global al subtipo): create/update/ignore.
    setServiceError(null);
    const permanenciaValue = Number(permanencia);
    if (zoneTypeId && subtipo && permanencia !== '' && permanenciaValue > 0) {
      try {
        const existing = await fetchDefaultServiceConfig(zoneTypeId, subtipo);
        let ok = true;
        if (!existing) {
          ok =
            (await createConfig({
              zone_type_id: zoneTypeId,
              subtipo,
              event_day_id: null,
              average_duration_min: permanenciaValue,
            })) !== null;
        } else if (existing.average_duration_min !== permanenciaValue) {
          ok =
            (await updateConfig(existing.id, {
              zone_type_id: zoneTypeId,
              subtipo,
              event_day_id: null,
              average_duration_min: permanenciaValue,
            })) !== null;
        }
        if (!ok) {
          setServiceError(
            'La zona se actualizó, pero no se pudo sincronizar la permanencia.'
          );
          return;
        }
      } catch (err) {
        console.error('[ZoneConfigModal] sync service_config falló:', err);
        setServiceError(
          'La zona se actualizó, pero no se pudo sincronizar la permanencia.'
        );
        return;
      }
    }

    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-800">Editar Zona</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nombre</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tipo</label>
            <select
              value={type}
              onChange={(e) => { setType(e.target.value); setSubtipo(''); }}
              className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
            >
              {ZONE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          {showSubtipoField && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Subtipo</label>
              {subtiposError ? (
                <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-md p-2">
                  No se pudieron cargar los subtipos. El valor actual se conserva al guardar.
                </p>
              ) : (
                <select
                  value={subtipo}
                  onChange={(e) => setSubtipo(e.target.value)}
                  disabled={subtiposLoading}
                  className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500 disabled:bg-slate-100"
                >
                  <option value="">
                    {subtiposLoading ? 'Cargando subtipos…' : 'Sin subtipo'}
                  </option>
                  {subtipos.map((s) => (
                    <option key={s.id} value={s.slug}>{s.name}</option>
                  ))}
                </select>
              )}
            </div>
          )}

          {showSubtipoField && subtipo !== '' && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Permanencia (min)
              </label>
              <input
                type="number"
                min={1}
                value={permanencia}
                onChange={(e) => setPermanencia(e.target.value)}
                placeholder="Ej: 15"
                className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="text-[10px] text-slate-400 mt-0.5">
                Se guarda globalmente para este subtipo (service_configs), no por zona.
              </p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Capacidad</label>
            <input
              type="number"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
              required
              min={1}
              className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Latitud</label>
              <input
                type="number"
                step="any"
                value={lat}
                onChange={(e) => setLat(e.target.value)}
                className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Longitud</label>
              <input
                type="number"
                step="any"
                value={lng}
                onChange={(e) => setLng(e.target.value)}
                className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <AdminMapSelector
            lat={lat ? Number(lat) : undefined}
            lng={lng ? Number(lng) : undefined}
            onChangeLocation={(newLat, newLng) => {
              setLat(String(newLat));
              setLng(String(newLng));
            }}
          />

          {serviceError && (
            <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-3">
              {serviceError}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="py-2 px-4 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="py-2 px-4 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md transition-colors"
            >
              {loading ? 'Guardando...' : 'Guardar Cambios'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
