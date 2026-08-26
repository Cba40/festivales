import { useState } from 'react';
import { useZoneCreation } from '../hooks/useZoneCreation';
import { useZoneTypes } from '../hooks/useZoneBehaviors';
import { useZoneSubtypes } from '../hooks/useZoneSubtypes';
import {
  useServiceConfigMutations,
} from '../hooks/useServiceConfigMutations';
import { fetchDefaultServiceConfig } from '../hooks/useServiceConfigs';
import { DEFAULTS_POR_SUBTIPO, TRANSPORTE_OPTIONS, ZONE_TYPES } from '../constants';
import { AdminMapSelector } from '../../../components/AdminMapSelector';

interface DynamicField {
  name: string;
  key: string;
  type: 'text' | 'number' | 'select' | 'checkbox';
  placeholder?: string;
  options?: { value: string; label: string }[];
  helperText?: string;
}

const dynamicFields: Record<string, DynamicField[]> = {
  estacionamiento: [
    { name: 'Disponibilidad (%)', key: 'disponibilidad', type: 'number', placeholder: '50' },
  ],
  transporte: [
    { name: 'Espera (min)', key: 'espera_min', type: 'number', placeholder: '10' },
    { name: 'Calle', key: 'calle', type: 'text', placeholder: 'Av. Principal' },
  ],
  comida: [
    { name: 'Espera (min)', key: 'espera_min', type: 'number', placeholder: '5' },
  ],
  emergencia: [
    { name: 'Dirección', key: 'direccion', type: 'text', placeholder: 'Av. Siempre Viva 123' },
    { name: 'Horario', key: 'horario', type: 'text', placeholder: '24hs' },
    { name: 'Teléfono', key: 'telefono', type: 'text', placeholder: '+543511234567' },
  ],
  descanso: [
    { name: 'X (0-100)', key: 'x', type: 'number', placeholder: '50' },
    { name: 'Y (0-100)', key: 'y', type: 'number', placeholder: '50' },
  ],
  salida: [
    {
      name: 'Modo de salida',
      key: 'transporte',
      type: 'select',
      placeholder: 'Seleccioná el modo de salida',
      options: TRANSPORTE_OPTIONS,
    },
    { name: 'Espera (min)', key: 'espera_min', type: 'number', placeholder: '5' },
    {
      name: '¿Es un punto de embudo?',
      key: 'es_embudo',
      type: 'checkbox',
      helperText: 'Marcá si esta salida concentra el flujo de egreso',
    },
  ],
};

interface Props {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function CreateZoneForm({ onSuccess, onCancel }: Props) {
  const { createZone, loading, error } = useZoneCreation();
  const { zoneTypes: catalogZoneTypes } = useZoneTypes();
  const [name, setName] = useState('');
  const [type, setType] = useState('estacionamiento');
  const [capacity, setCapacity] = useState('');
  const [lat, setLat] = useState('');
  const [lng, setLng] = useState('');
  const [subtipo, setSubtipo] = useState('');
  const [permanencia, setPermanencia] = useState('');
  const [serviceError, setServiceError] = useState<string | null>(null);
  const [extra, setExtra] = useState<Record<string, string>>({});
  const { create: createConfig, update: updateConfig } =
    useServiceConfigMutations();

  // slug → id del catálogo zone_types para consultar los subtipos del tipo elegido.
  const selectedTypeRow = catalogZoneTypes.find((t) => t.slug === type) ?? null;
  const zoneTypeId = selectedTypeRow?.id ?? null;
  const {
    data: subtipos,
    isLoading: subtiposLoading,
    error: subtiposError,
  } = useZoneSubtypes(zoneTypeId);

  const showSubtipoField =
    zoneTypeId !== null && (subtipos.length > 0 || subtiposLoading || subtiposError !== null);

  // Al elegir subtipo: precarga la permanencia existente en service_configs
  // (default global) o el default sugerido si aún no hay config.
  const handleSubtipoChange = async (slug: string) => {
    setSubtipo(slug);
    setServiceError(null);
    if (!slug || !zoneTypeId) {
      setPermanencia('');
      return;
    }
    try {
      const config = await fetchDefaultServiceConfig(zoneTypeId, slug);
      if (config) {
        setPermanencia(config.average_duration_min.toString());
      } else {
        setPermanencia(
          (DEFAULTS_POR_SUBTIPO[slug] ?? '').toString()
        );
      }
    } catch (err) {
      console.error('[CreateZoneForm] lookup service_config falló:', err);
      setPermanencia((DEFAULTS_POR_SUBTIPO[slug] ?? '').toString());
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !capacity || Number(capacity) <= 0) return;
    if (type === 'salida' && !extra.transporte) return;

    const extraPayload: Record<string, string | number | boolean> = {};
    for (const [k, v] of Object.entries(extra)) {
      if (v === 'true') extraPayload[k] = true;
      else if (v === 'false') extraPayload[k] = false;
      else if (v && !isNaN(Number(v))) extraPayload[k] = Number(v);
      else extraPayload[k] = v;
    }

    if (type === 'salida') {
      extraPayload.capacidad_estimada = Number(capacity);
    }

    // a) Crear la zona primero.
    const created = await createZone({
      name: name.trim(),
      type,
      capacity: Number(capacity),
      lat: lat ? Number(lat) : undefined,
      lng: lng ? Number(lng) : undefined,
      ...(subtipo ? { subtipo } : {}),
      ...extraPayload,
    });

    if (!created) return; // la zona falló: el error ya se muestra; no tocar configs.

    // b-d) Sincronizar service_configs (global al subtipo). La zona ya está
    // creada: si esto falla se informa pero NO se revierte.
    setServiceError(null);
    const permanenciaValue = Number(permanencia);
    if (subtipo && zoneTypeId && permanencia !== '' && permanenciaValue > 0) {
      try {
        const existing = await fetchDefaultServiceConfig(zoneTypeId, subtipo);
        if (!existing) {
          const ok = await createConfig({
            zone_type_id: zoneTypeId,
            subtipo,
            event_day_id: null,
            average_duration_min: permanenciaValue,
          });
          if (!ok) {
            setServiceError('La zona se creó, pero no se pudo guardar la permanencia.');
          }
        } else if (existing.average_duration_min !== permanenciaValue) {
          const ok = await updateConfig(existing.id, {
            average_duration_min: permanenciaValue,
          });
          if (!ok) {
            setServiceError('La zona se creó, pero no se pudo actualizar la permanencia.');
          }
        }
        // e) Si existe y el valor no cambió: no hacer nada.
      } catch (err) {
        console.error('[CreateZoneForm] sync service_config falló:', err);
        setServiceError('La zona se creó, pero no se pudo sincronizar la permanencia.');
      }
    }

    setName('');
    setType('estacionamiento');
    setCapacity('');
    setLat('');
    setLng('');
    setSubtipo('');
    setPermanencia('');
    setExtra({});
    if (onSuccess) onSuccess();
  };

  const fields = dynamicFields[type] || [];

  return (
    <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg border border-slate-200 space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Nombre de la Zona</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          placeholder="Ej: Estacionamiento Este"
          className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Tipo</label>
        <select
          value={type}
          onChange={(e) => { setType(e.target.value); setSubtipo(''); setExtra({}); }}
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
              No se pudieron cargar los subtipos. La zona se creará sin subtipo.
            </p>
          ) : (
            <select
              value={subtipo}
              onChange={(e) => { void handleSubtipoChange(e.target.value); }}
              disabled={subtiposLoading}
              className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500 disabled:bg-slate-100"
            >
              <option value="">
                {subtiposLoading ? 'Cargando subtipos…' : 'Seleccioná un subtipo (opcional)'}
              </option>
              {subtipos.map((s) => (
                <option key={s.id} value={s.slug}>{s.name}</option>
              ))}
            </select>
          )}
        </div>
      )}

      {showSubtipoField && (
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
          placeholder="350"
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
            placeholder="-30.9733"
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
            placeholder="-64.0885"
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

      {fields.map((f) => {
        if (f.type === 'select') {
          return (
            <div key={f.key}>
              <label className="block text-sm font-medium text-slate-700 mb-1">{f.name}</label>
              <select
                value={extra[f.key] || ''}
                onChange={(e) => setExtra(prev => ({ ...prev, [f.key]: e.target.value }))}
                className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="" disabled>{f.placeholder}</option>
                {(f.options ?? []).map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          );
        }
        if (f.type === 'checkbox') {
          return (
            <div key={f.key}>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  checked={extra[f.key] === 'true'}
                  onChange={(e) => setExtra(prev => ({ ...prev, [f.key]: e.target.checked ? 'true' : 'false' }))}
                  className="accent-emerald-600"
                />
                {f.name}
              </label>
              {f.helperText && (
                <p className="text-xs text-slate-500 mt-1 ml-6">{f.helperText}</p>
              )}
            </div>
          );
        }
        return (
          <div key={f.key}>
            <label className="block text-sm font-medium text-slate-700 mb-1">{f.name}</label>
            <input
              type={f.type}
              value={extra[f.key] || ''}
              onChange={(e) => setExtra(prev => ({ ...prev, [f.key]: e.target.value }))}
              placeholder={f.placeholder}
              className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        );
      })}

      {type === 'salida' && !extra.transporte && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
          Seleccioná el modo de salida para poder crear la zona.
        </p>
      )}

      {error && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
          {error}
        </div>
      )}

      {!error && serviceError && (
        <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-3">
          {serviceError}
        </div>
      )}

      <div className="flex justify-end gap-3 pt-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="py-2 px-4 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
          >
            Cancelar
          </button>
        )}
        <button
          type="submit"
          disabled={loading || (type === 'salida' && !extra.transporte)}
          className="py-2 px-4 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md transition-colors"
        >
          {loading ? 'Creando...' : 'Crear Zona'}
        </button>
      </div>
    </form>
  );
}
