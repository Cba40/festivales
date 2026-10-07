import { useState, useEffect } from 'react';
import { useZoneConfigMutations } from '../hooks/useZoneConfigMutations';
import { useZoneTypes } from '../hooks/useZoneBehaviors';
import { useZoneSubtypes } from '../hooks/useZoneSubtypes';
import { resolveServiceConfigForEventDay } from '../hooks/useServiceConfigs';
import { useServiceConfigMutations } from '../hooks/useServiceConfigMutations';
import {
  isBathroomSubtipo,
  parseBathroomUseRate,
  formatUseRate,
} from '../utils/bathroomUseRate';
import type { ServiceConfigCreatePayload, Zone } from '../types';
import { DEFAULTS_POR_SUBTIPO, TRANSPORTE_OPTIONS, ZONE_TYPES } from '../constants';
import { AdminMapSelector } from '../../../components/AdminMapSelector';
import { Button } from './ui/Button';
import { BathroomUseRateField } from './ui/BathroomUseRateField';
import { useAppStore } from '@/core/state/store';

interface Props {
  zone: Zone;
  onClose: () => void;
}

export function ZoneConfigModal({ zone, onClose }: Props) {
  const { updateZone, patchZoneFields, loading } = useZoneConfigMutations();
  const { create: createConfig, update: updateConfig } =
    useServiceConfigMutations();
  const { zoneTypes } = useZoneTypes();
  const eventDayId = useAppStore((s) => s.eventDayId);
  const [name, setName] = useState(zone.name);
  const [type, setType] = useState(zone.type);
  const [capacity, setCapacity] = useState(String(zone.capacity));
  const [lat, setLat] = useState(zone.lat !== undefined ? String(zone.lat) : '');
  const [lng, setLng] = useState(zone.lng !== undefined ? String(zone.lng) : '');
  const [subtipo, setSubtipo] = useState(zone.subtipo || '');
  const [permanencia, setPermanencia] = useState('');
  const [useRate, setUseRate] = useState('');
  const [useRateError, setUseRateError] = useState<string | null>(null);
  const [transporte, setTransporte] = useState(zone.transporte ?? '');
  const [esperaMin, setEsperaMin] = useState(
    zone.espera_min !== undefined && zone.espera_min !== null ? String(zone.espera_min) : ''
  );
  const [esEmbudo, setEsEmbudo] = useState(zone.es_embudo === true);
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
  const isBathroom = showSubtipoField && subtipo !== '' && isBathroomSubtipo(subtipo);

  useEffect(() => {
    setName(zone.name);
    setType(zone.type);
    setCapacity(String(zone.capacity));
    setLat(zone.lat !== undefined ? String(zone.lat) : '');
    setLng(zone.lng !== undefined ? String(zone.lng) : '');
    setSubtipo(zone.subtipo || '');
    setTransporte(zone.transporte ?? '');
    setEsperaMin(
      zone.espera_min !== undefined && zone.espera_min !== null ? String(zone.espera_min) : ''
    );
    setEsEmbudo(zone.es_embudo === true);
    setServiceError(null);
    setUseRateError(null);
  }, [zone]);

  // Precarga la permanencia y la tasa de la JORNADA ACTIVA: override si existe,
  // si no el default global como referencia visual.
  useEffect(() => {
    let cancelled = false;
    if (!zoneTypeId || !subtipo) {
      setPermanencia('');
      setUseRate('');
      return;
    }
    const load = async () => {
      try {
        const { config } =
          await resolveServiceConfigForEventDay(zoneTypeId, subtipo, eventDayId);
        if (!cancelled) {
          setPermanencia(
            config
              ? String(config.average_duration_min)
              : String(DEFAULTS_POR_SUBTIPO[subtipo] ?? '')
          );
          setUseRate(
            config
              ? formatUseRate(config.bathroom_use_rate_per_person_hour)
              : isBathroomSubtipo(subtipo)
                ? formatUseRate(null)
                : ''
          );
        }
      } catch (err) {
        console.error('[ZoneConfigModal] lookup service_config falló:', err);
        if (!cancelled) {
          setPermanencia(String(DEFAULTS_POR_SUBTIPO[subtipo] ?? ''));
          setUseRate(isBathroomSubtipo(subtipo) ? formatUseRate(null) : '');
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [zoneTypeId, subtipo, eventDayId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !capacity || Number(capacity) <= 0) return;
    if (type === 'salida' && !transporte) return;

    // Validar la tasa antes de tocar nada.
    let useRateValue: number | null = null;
    if (isBathroom) {
      const parsed = parseBathroomUseRate(useRate);
      if (!parsed.ok) {
        setUseRateError(parsed.error);
        return;
      }
      setUseRateError(null);
      useRateValue = parsed.value;
    }

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

    // 3) Campos dinámicos de salida: PUT /config no los acepta → PATCH.
    // capacidad_estimada se mantiene espejando capacity (igual que en creación).
    if (type === 'salida') {
      const okSalida = await patchZoneFields(zone.id, {
        transporte,
        espera_min: esperaMin === '' ? null : Number(esperaMin),
        es_embudo: esEmbudo,
        capacidad_estimada: Number(capacity),
      });
      if (!okSalida) {
        console.error('[ZoneConfigModal] persistir campos de salida falló');
        setServiceError('La zona se actualizó, pero no se pudieron guardar los datos de salida.');
        return;
      }
    }

    // 4) Sincronizar service_configs (global al subtipo): create/update/ignore.
    setServiceError(null);
    const permanenciaValue = Number(permanencia);
    if (zoneTypeId && subtipo && permanencia !== '' && permanenciaValue > 0) {
      try {
        const { config: existing, targetEventDayId: target } =
          await resolveServiceConfigForEventDay(zoneTypeId, subtipo, eventDayId);
        const payload: ServiceConfigCreatePayload = {
          zone_type_id: zoneTypeId,
          subtipo,
          event_day_id: target,
          average_duration_min: permanenciaValue,
          ...(useRateValue !== null
            ? { bathroom_use_rate_per_person_hour: useRateValue }
            : {}),
        };
        const useRateChanged =
          useRateValue !== null &&
          existing?.bathroom_use_rate_per_person_hour !== useRateValue;
        // `ServiceConfigUpdate` no acepta `event_day_id`: un PUT sobre el
        // default global jamás crearía el override de la jornada. Solo se
        // actualiza si la fila ya es del ámbito destino.
        const isSameScope =
          existing !== null && existing.event_day_id === target;
        let ok = true;
        if (!isSameScope) {
          ok = (await createConfig(payload)) !== null;
        } else if (
          existing.average_duration_min !== permanenciaValue ||
          useRateChanged
        ) {
          ok = (await updateConfig(existing.id, payload)) !== null;
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-6xl max-h-[90vh] overflow-y-auto">
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
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tipo</label>
            <select
              value={type}
              onChange={(e) => { setType(e.target.value); setSubtipo(''); }}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
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
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-slate-100"
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
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
              <p className="text-[10px] text-slate-400 mt-0.5">
                Se guarda globalmente para este subtipo (service_configs), no por zona.
              </p>
            </div>
          )}

          {isBathroom && (
            <BathroomUseRateField
              value={useRate}
              onChange={(v) => {
                setUseRate(v);
                if (useRateError) setUseRateError(null);
              }}
              error={useRateError}
            />
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Capacidad</label>
            <input
              type="number"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
              required
              min={1}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
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
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Longitud</label>
              <input
                type="number"
                step="any"
                value={lng}
                onChange={(e) => setLng(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
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

          {type === 'salida' && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Modo de salida</label>
                <select
                  value={transporte}
                  onChange={(e) => setTransporte(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="" disabled>Seleccioná el modo de salida</option>
                  {TRANSPORTE_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Espera (min)</label>
                <input
                  type="number"
                  min={0}
                  value={esperaMin}
                  onChange={(e) => setEsperaMin(e.target.value)}
                  placeholder="Ej: 5"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <input
                    type="checkbox"
                    checked={esEmbudo}
                    onChange={(e) => setEsEmbudo(e.target.checked)}
                    className="accent-indigo-600"
                  />
                  ¿Es un punto de embudo?
                </label>
                <p className="text-xs text-slate-500 mt-1 ml-6">
                  Marcá si esta salida concentra el flujo de egreso
                </p>
              </div>
              {!transporte && (
                <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
                  Seleccioná el modo de salida para poder guardar los cambios.
                </p>
              )}
            </>
          )}

          {serviceError && (
            <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-3">
              {serviceError}
            </div>
          )}

          <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={loading || (type === 'salida' && !transporte)}
            >
              {loading ? 'Guardando...' : 'Guardar Cambios'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
