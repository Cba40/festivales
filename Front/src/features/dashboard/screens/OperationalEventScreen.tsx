import { useState, useCallback, useEffect, useMemo } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import { useOperationalEvents } from '../hooks/useOperationalEvents';
import { useOperationalEventMutations } from '../hooks/useOperationalEventMutations';
import { useEventDays } from '../hooks/useEventDays';
import { FlowRestrictionSection } from '../components/FlowRestrictionSection';
import type {
  OperationalEventDTO,
  OperationalEventCreatePayload,
  OperationalEventUpdatePayload,
  OperationalEffectType,
} from '../types';

const DEFAULT_EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

interface ZoneOption {
  id: string;
  name: string;
  type: string;
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  accidente: 'Accidente',
  corte_calle: 'Corte de calle',
  tormenta: 'Tormenta',
  evacuacion: 'Evacuación',
  incendio: 'Incendio',
  congestion_extraordinaria: 'Congestión Extraordinaria',
  escenario_finalizado: 'Escenario Finalizado',
  apertura_extraordinaria: 'Apertura Extraordinaria',
  incidente_operativo: 'Incidente Operativo',
  fin_espectaculo: 'Fin de Espectáculo',
  corte_energia: 'Corte de Energía',
};

const EVENT_TYPE_ICONS: Record<string, string> = {
  accidente: '⚠️',
  corte_calle: '🚧',
  tormenta: '⛈️',
  evacuacion: '🚨',
  incendio: '🔥',
  congestion_extraordinaria: '🚗',
  escenario_finalizado: '🎭',
  apertura_extraordinaria: '🚪',
  incidente_operativo: '🔧',
  fin_espectaculo: '🎵',
  corte_energia: '💡',
};

const EFFECT_TYPE_LABELS: Record<OperationalEffectType, string> = {
  reduccion_capacidad: 'Reducción de capacidad',
  cierre_total: 'Cierre total',
  aumento_demanda: 'Aumento de demanda',
  incidente_sin_impacto: 'Incidente sin impacto',
};

function toLocalDateTimeInput(d: Date): string {
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function isoToLocalDateTimeInput(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  return toLocalDateTimeInput(d);
}

function localDateTimeToIso(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  return isNaN(d.getTime()) ? null : d.toISOString();
}

function isExpired(endTimestamp: string): boolean {
  return Date.now() >= new Date(endTimestamp).getTime();
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString('es-AR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function validateEffectValue(
  effectType: OperationalEffectType,
  value: string,
): boolean {
  if (effectType === 'reduccion_capacidad' || effectType === 'aumento_demanda') {
    const n = Number(value);
    if (!Number.isFinite(n)) return false;
    if (effectType === 'reduccion_capacidad') return n >= 1 && n <= 100;
    return n >= 1;
  }
  return true;
}

function validateTemporal(
  startStr: string,
  endStr: string,
): boolean {
  const s = new Date(startStr);
  const e = new Date(endStr);
  if (isNaN(s.getTime()) || isNaN(e.getTime())) return false;
  return e > s;
}

function validateCoordinate(value: string, min: number, max: number): boolean {
  if (value.trim() === '') return true;
  const n = Number(value);
  return Number.isFinite(n) && n >= min && n <= max;
}

interface EventFormData {
  event_type: string;
  description: string;
  zone_id: string;
  effect_type: string;
  effect_value: string;
  is_incident: boolean;
  start_timestamp: string;
  end_timestamp: string;
  latitude: string;
  longitude: string;
}

const emptyForm: EventFormData = {
  event_type: '',
  description: '',
  zone_id: '',
  effect_type: '',
  effect_value: '',
  is_incident: false,
  start_timestamp: '',
  end_timestamp: '',
  latitude: '',
  longitude: '',
};

function getStatus(
  event: OperationalEventDTO,
): 'Activo' | 'Finalizado' | 'Expirado' {
  if (!event.is_active) return 'Finalizado';
  if (isExpired(event.end_timestamp)) return 'Expirado';
  return 'Activo';
}

const STATUS_CLASSES: Record<string, string> = {
  Activo: 'text-xs font-bold uppercase text-red-600 bg-red-100 px-2 py-0.5 rounded-full animate-pulse',
  Finalizado: 'text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full',
  Expirado: 'text-xs font-bold uppercase text-amber-600 bg-amber-100 px-2 py-0.5 rounded-full',
};

function EventCard({
  event,
  onFinalize,
  onEdit,
  onDelete,
  saving,
  zoneName,
}: {
  event: OperationalEventDTO;
  onFinalize: (id: string) => void;
  onEdit: (e: OperationalEventDTO) => void;
  onDelete: (id: string) => void;
  saving: boolean;
  zoneName?: string;
}) {
  const status = getStatus(event);
  const expired = isExpired(event.end_timestamp);
  const lock = expired;

  return (
    <div
      className={`rounded-xl border-2 p-4 transition-all ${
        event.is_active && !expired
          ? 'border-red-300 bg-red-50 shadow-md'
          : 'border-slate-200 bg-white opacity-70'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <span className="text-2xl flex-shrink-0 mt-0.5">
            {EVENT_TYPE_ICONS[event.event_type] ?? '📌'}
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold text-slate-800">
                {EVENT_TYPE_LABELS[event.event_type] ?? event.event_type}
              </span>
              <span className={STATUS_CLASSES[status]}>{status}</span>
              {event.is_incident && (
                <span className="text-xs font-bold uppercase text-purple-600 bg-purple-100 px-2 py-0.5 rounded-full">
                  Incidente
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span className="font-medium text-slate-600">
                {EFFECT_TYPE_LABELS[event.effect_type] ?? event.effect_type}
              </span>
              {event.effect_value !== null && (
                <span className="text-slate-700 font-semibold">
                  {event.effect_type === 'reduccion_capacidad'
                    ? `-${event.effect_value}%`
                    : event.effect_type === 'aumento_demanda'
                      ? `+${event.effect_value} pers.`
                      : event.effect_value}
                </span>
              )}
            </div>

            {event.description && (
              <p className="text-sm text-slate-600 mt-1 break-words">{event.description}</p>
            )}

            <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
              <span>Inicio: {formatTimestamp(event.start_timestamp)}</span>
              <span>Fin: {formatTimestamp(event.end_timestamp)}</span>
              {event.zone_id && <span>Zona: {zoneName ?? event.zone_id}</span>}
            </div>
            {event.latitude != null && event.longitude != null && (
              <div className="text-xs text-slate-400 mt-0.5">
                Ubicación: {event.latitude}, {event.longitude}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          {event.is_active && !expired && (
            <button
              onClick={() => onFinalize(event.id)}
              disabled={saving}
              className="text-xs font-medium px-2.5 py-1.5 rounded bg-green-600 hover:bg-green-700 text-white disabled:opacity-50"
            >
              Finalizar
            </button>
          )}
          <button
            onClick={() => onEdit(event)}
            disabled={lock}
            className="text-xs font-medium px-2.5 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Editar
          </button>
          <button
            onClick={() => onDelete(event.id)}
            disabled={saving || lock}
            className="text-xs font-medium px-2.5 py-1.5 rounded bg-red-100 hover:bg-red-200 text-red-600 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Eliminar
          </button>
        </div>
      </div>
    </div>
  );
}

function EventFormModal({
  initial,
  eventDayId,
  zones,
  onSave,
  onClose,
  saving,
}: {
  initial: EventFormData;
  eventDayId: string;
  zones: ZoneOption[];
  onSave: (payload: OperationalEventCreatePayload | OperationalEventUpdatePayload) => void;
  onClose: () => void;
  saving: boolean;
}) {
  const [form, setForm] = useState<EventFormData>(initial);
  const [zoneQuery, setZoneQuery] = useState('');
  const [zoneOpen, setZoneOpen] = useState(false);
  const isEditing = !!initial.zone_id && initial.zone_id !== '';
  const isEditingMode = isEditing && initial.event_type !== '';

  const displayedZone = zones.find((z) => z.id === form.zone_id);

  useEffect(() => {
    if (isEditingMode && !zoneQuery && displayedZone) {
      setZoneQuery(displayedZone.name);
    }
  }, [isEditingMode, zoneQuery, displayedZone]);

  const filteredZones = zones
    .filter((z) => z.name.toLowerCase().includes(zoneQuery.trim().toLowerCase()))
    .slice(0, 8);

  const handleZoneSelect = (zone: ZoneOption) => {
    setForm((f) => ({ ...f, zone_id: zone.id }));
    setZoneQuery(zone.name);
    setZoneOpen(false);
  };

  const effectType = form.effect_type as OperationalEffectType | '';
  const needsValue = effectType === 'reduccion_capacidad' || effectType === 'aumento_demanda';

  const temporalOk = form.start_timestamp && form.end_timestamp
    ? validateTemporal(form.start_timestamp, form.end_timestamp)
    : false;

  const effectValueOk = needsValue
    ? validateEffectValue(effectType, form.effect_value)
    : true;

  const coordsOk =
    validateCoordinate(form.latitude, -90, 90) &&
    validateCoordinate(form.longitude, -180, 180);

  const canSubmit =
    !saving &&
    !!form.event_type &&
    !!form.zone_id.trim() &&
    !!form.effect_type &&
    !!form.start_timestamp &&
    !!form.end_timestamp &&
    temporalOk &&
    effectValueOk &&
    coordsOk;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    const startIso = localDateTimeToIso(form.start_timestamp)!;
    const endIso = localDateTimeToIso(form.end_timestamp)!;
    const latitude = form.latitude.trim() === '' ? null : Number(form.latitude);
    const longitude = form.longitude.trim() === '' ? null : Number(form.longitude);

    if (isEditingMode) {
      const payload: OperationalEventUpdatePayload = {
        event_type: form.event_type as OperationalEventUpdatePayload['event_type'],
        description: form.description.trim() || null,
        effect_type: form.effect_type as OperationalEffectType,
        effect_value: needsValue ? Math.round(Number(form.effect_value)) : null,
        is_incident: form.is_incident,
        start_timestamp: startIso,
        end_timestamp: endIso,
        latitude,
        longitude,
      };
      onSave(payload);
    } else {
      const payload: OperationalEventCreatePayload = {
        event_day_id: eventDayId,
        zone_id: form.zone_id.trim(),
        event_type: form.event_type as OperationalEventCreatePayload['event_type'],
        description: form.description.trim() || null,
        effect_type: form.effect_type as OperationalEffectType,
        effect_value: needsValue ? Math.round(Number(form.effect_value)) : null,
        is_incident: form.is_incident,
        start_timestamp: startIso,
        end_timestamp: endIso,
        latitude,
        longitude,
      };
      onSave(payload);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-slate-800 mb-4">
          {isEditingMode ? 'Editar Evento' : 'Nuevo Evento Operativo'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Tipo de evento */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tipo de evento *</label>
            <select
              value={form.event_type}
              onChange={(e) => setForm((f) => ({ ...f, event_type: e.target.value }))}
              required
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Seleccionar...</option>
              {Object.entries(EVENT_TYPE_LABELS).map(([key, label]) => (
                <option key={key} value={key}>{EVENT_TYPE_ICONS[key]} {label}</option>
              ))}
            </select>
          </div>

          {/* Zona — búsqueda y selección por nombre */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Zona *</label>
            <div className="relative">
              <input
                type="text"
                value={zoneQuery}
                onChange={(e) => {
                  setZoneQuery(e.target.value);
                  setZoneOpen(true);
                  if (!isEditingMode) {
                    setForm((f) => ({ ...f, zone_id: '' }));
                  }
                }}
                onFocus={() => setZoneOpen(true)}
                onBlur={() => setTimeout(() => setZoneOpen(false), 120)}
                readOnly={isEditingMode}
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 read-only:bg-slate-50 read-only:cursor-not-allowed"
                placeholder="Buscar zona por nombre (ej: Estacionamiento Norte, Baños Sector A)..."
              />
              {zoneOpen && !isEditingMode && filteredZones.length > 0 && (
                <ul className="absolute z-10 mt-1 w-full max-h-56 overflow-auto bg-white border border-slate-200 rounded-lg shadow-xl divide-y divide-slate-100">
                  {filteredZones.map((z) => (
                    <li key={z.id}>
                      <button
                        type="button"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => handleZoneSelect(z)}
                        className="w-full text-left px-3 py-2 text-sm text-slate-700 hover:bg-blue-50"
                      >
                        <span className="font-medium">{z.name}</span>
                        {z.type && (
                          <span className="ml-2 text-xs text-slate-400">
                            {EVENT_TYPE_ICONS[z.type] ?? ''} {z.type}
                          </span>
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {zoneOpen && !isEditingMode && zones.length === 0 && zoneQuery.trim() !== '' && (
                <div className="absolute z-10 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-xl px-3 py-2 text-sm text-slate-500">
                  Sin coincidencias. No se pudieron cargar las zonas disponibles.
                </div>
              )}
            </div>
            {form.zone_id && displayedZone && (
              <p className="text-xs text-slate-500 mt-1">Zona seleccionada: {displayedZone.name}</p>
            )}
          </div>

          {/* Effect type */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tipo de efecto *</label>
            <select
              value={form.effect_type}
              onChange={(e) =>
                setForm((f) => ({ ...f, effect_type: e.target.value, effect_value: '' }))
              }
              required
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Seleccionar...</option>
              {Object.entries(EFFECT_TYPE_LABELS).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </div>

          {/* Effect value — conditional */}
          {needsValue && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {effectType === 'reduccion_capacidad'
                  ? 'Porcentaje de reducción (1-100)% *'
                  : 'Personas adicionales (≥ 1) *'}
              </label>
              <input
                type="number"
                value={form.effect_value}
                onChange={(e) => setForm((f) => ({ ...f, effect_value: e.target.value }))}
                min={effectType === 'reduccion_capacidad' ? 1 : 1}
                max={effectType === 'reduccion_capacidad' ? 100 : undefined}
                required
                className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  form.effect_value && !effectValueOk
                    ? 'border-red-400 bg-red-50'
                    : 'border-slate-300'
                }`}
                placeholder={effectType === 'reduccion_capacidad' ? '1-100' : '≥ 1'}
              />
              {form.effect_value && !effectValueOk && (
                <p className="text-xs text-red-500 mt-1">
                  {effectType === 'reduccion_capacidad'
                    ? 'Debe estar entre 1 y 100'
                    : 'Debe ser al menos 1'}
                </p>
              )}
            </div>
          )}

          {/* Is incident toggle */}
          <div className="flex items-center gap-3 py-1">
            <input
              type="checkbox"
              id="is_incident"
              checked={form.is_incident}
              onChange={(e) => setForm((f) => ({ ...f, is_incident: e.target.checked }))}
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="is_incident" className="text-sm font-medium text-slate-700 select-none cursor-pointer">
              ¿Es un incidente operativo?
            </label>
          </div>

          {/* Datetime pickers */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Fecha y hora inicio *</label>
              <input
                type="datetime-local"
                value={form.start_timestamp}
                onChange={(e) => setForm((f) => ({ ...f, start_timestamp: e.target.value }))}
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Fecha y hora fin *</label>
              <input
                type="datetime-local"
                value={form.end_timestamp}
                onChange={(e) => setForm((f) => ({ ...f, end_timestamp: e.target.value }))}
                required
                className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  form.start_timestamp && form.end_timestamp && !temporalOk
                    ? 'border-red-400 bg-red-50'
                    : 'border-slate-300'
                }`}
              />
              {form.start_timestamp && form.end_timestamp && !temporalOk && (
                <p className="text-xs text-red-500 mt-1">La fecha fin debe ser posterior al inicio</p>
              )}
            </div>
          </div>

          {/* Coordenadas opcionales */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Ubicación física del hecho (opcional)
            </label>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Latitud (-90 a 90)</label>
                <input
                  type="number"
                  step="any"
                  value={form.latitude}
                  onChange={(e) => setForm((f) => ({ ...f, latitude: e.target.value }))}
                  className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    form.latitude && !validateCoordinate(form.latitude, -90, 90)
                      ? 'border-red-400 bg-red-50'
                      : 'border-slate-300'
                  }`}
                  placeholder="Ej: -31.4201"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Longitud (-180 a 180)</label>
                <input
                  type="number"
                  step="any"
                  value={form.longitude}
                  onChange={(e) => setForm((f) => ({ ...f, longitude: e.target.value }))}
                  className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    form.longitude && !validateCoordinate(form.longitude, -180, 180)
                      ? 'border-red-400 bg-red-50'
                      : 'border-slate-300'
                  }`}
                  placeholder="Ej: -64.1888"
                />
              </div>
            </div>
            {!coordsOk && (
              <p className="text-xs text-red-500 mt-1">
                Latitud debe estar entre -90 y 90; longitud entre -180 y 180.
              </p>
            )}
          </div>

          {/* Description (optional) */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Descripción</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              rows={3}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Detalles del evento (opcional)..."
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={!canSubmit}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-lg text-sm disabled:opacity-50"
            >
              {saving ? 'Guardando...' : isEditingMode ? 'Guardar Cambios' : 'Registrar Evento'}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm text-slate-600 hover:bg-slate-50"
            >
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function OperationalEventScreen() {
  const { eventDays, loading: loadingDays } = useEventDays(DEFAULT_EVENT_ID);
  const [selectedDayId, setSelectedDayId] = useState<string | null>(null);
  const { events, loading, error, refresh } = useOperationalEvents(selectedDayId);
  const { create, update, remove, deactivate, saving, error: mutationError } = useOperationalEventMutations();
  const [showForm, setShowForm] = useState(false);
  const [editingEvent, setEditingEvent] = useState<OperationalEventDTO | null>(null);
  const [showFinalized, setShowFinalized] = useState(false);
  const [activeSection, setActiveSection] = useState<'events' | 'restriction'>('events');
  const [zones, setZones] = useState<ZoneOption[]>([]);

  const loadZones = useCallback(async () => {
    try {
      const res = await apiClient.get<ZoneOption[]>(endpoints.zones.list(DEFAULT_EVENT_ID));
      setZones(res.data.filter((z) => z && z.id && z.name));
    } catch {
      setZones([]);
    }
  }, []);

  useEffect(() => {
    void loadZones();
  }, [loadZones]);

  const zoneNameById = useMemo(() => {
    const map: Record<string, string> = {};
    for (const z of zones) map[z.id] = z.name;
    return map;
  }, [zones]);

  useEffect(() => {
    if (eventDays.length > 0 && !selectedDayId) {
      setSelectedDayId(eventDays[0].id);
    }
  }, [eventDays, selectedDayId]);

  const activeEvents = useMemo(
    () => events.filter((e) => e.is_active && !isExpired(e.end_timestamp)),
    [events],
  );
  const expiredEvents = useMemo(
    () => events.filter((e) => e.is_active && isExpired(e.end_timestamp)),
    [events],
  );
  const finalizedEvents = useMemo(
    () => events.filter((e) => !e.is_active),
    [events],
  );

  const handleSave = useCallback(
    async (payload: OperationalEventCreatePayload | OperationalEventUpdatePayload) => {
      let result;
      if (editingEvent) {
        result = await update(editingEvent.id, payload as OperationalEventUpdatePayload);
      } else {
        result = await create(payload as OperationalEventCreatePayload);
      }
      if (result) {
        setShowForm(false);
        setEditingEvent(null);
        refresh();
      }
    },
    [editingEvent, create, update, refresh],
  );

  const handleEdit = useCallback((event: OperationalEventDTO) => {
    setEditingEvent(event);
    setShowForm(true);
  }, []);

  const handleDeactivate = useCallback(
    async (id: string) => {
      const result = await deactivate(id);
      if (result) refresh();
    },
    [deactivate, refresh],
  );

  const handleDelete = useCallback(
    async (id: string) => {
      const ok = await remove(id);
      if (ok) refresh();
    },
    [remove, refresh],
  );

  const openCreateForm = useCallback(() => {
    setEditingEvent(null);
    setShowForm(true);
  }, []);

  const closeForm = useCallback(() => {
    setShowForm(false);
    setEditingEvent(null);
  }, []);

  const formInitial: EventFormData = editingEvent
    ? {
        event_type: editingEvent.event_type,
        description: editingEvent.description ?? '',
        zone_id: editingEvent.zone_id,
        effect_type: editingEvent.effect_type,
        effect_value: editingEvent.effect_value?.toString() ?? '',
        is_incident: editingEvent.is_incident,
        start_timestamp: isoToLocalDateTimeInput(editingEvent.start_timestamp),
        end_timestamp: isoToLocalDateTimeInput(editingEvent.end_timestamp),
        latitude: editingEvent.latitude?.toString() ?? '',
        longitude: editingEvent.longitude?.toString() ?? '',
      }
    : emptyForm;

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold text-slate-800">Eventos Operativos</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={refresh}
            disabled={loading}
            className="text-sm px-3 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-600 font-medium"
          >
            {loading ? 'Cargando...' : 'Actualizar'}
          </button>
          <button
            onClick={openCreateForm}
            disabled={activeSection !== 'events'}
            className="bg-red-600 hover:bg-red-700 text-white px-4 py-1.5 rounded-lg text-sm font-bold shadow-sm disabled:opacity-50"
          >
            + Nuevo Evento
          </button>
        </div>
      </header>

      <main className="p-6 max-w-4xl mx-auto">
        {/* Sub-tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveSection('events')}
            className={`text-sm font-medium px-4 py-2 rounded-lg transition-colors ${
              activeSection === 'events'
                ? 'bg-red-600 text-white'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
            }`}
          >
            Eventos puntuales
          </button>
          <button
            onClick={() => setActiveSection('restriction')}
            className={`text-sm font-medium px-4 py-2 rounded-lg transition-colors ${
              activeSection === 'restriction'
                ? 'bg-red-600 text-white'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
            }`}
          >
            Restricción por tipo y fase
          </button>
        </div>

        {mutationError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {mutationError}
          </div>
        )}

        {activeSection === 'events' ? (
          <>
            {error && (
              <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
                {error}
              </div>
            )}

            {/* EventDay selector */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-700 mb-1">Jornada</label>
              <select
                value={selectedDayId ?? ''}
                onChange={(e) => setSelectedDayId(e.target.value || null)}
                disabled={loadingDays}
                className="w-full max-w-xs px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              >
                <option value="">Seleccionar jornada...</option>
                {eventDays.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.date} — {d.day_of_week}
                  </option>
                ))}
              </select>
            </div>

            {!selectedDayId ? (
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-10 text-center text-slate-500">
                Seleccioná una jornada para ver sus eventos operativos.
              </div>
            ) : loading ? (
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-10 text-center text-slate-500">
                Cargando eventos...
              </div>
            ) : (
              <>
                {/* Active events */}
                <section className="mb-8">
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                      <span className="w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse" />
                      Eventos Activos
                      <span className="text-sm font-normal text-slate-500">({activeEvents.length})</span>
                    </h2>
                  </div>
                  {activeEvents.length === 0 ? (
                    <div className="bg-white rounded-xl border-2 border-dashed border-slate-200 p-8 text-center text-slate-400">
                      No hay eventos activos en esta jornada.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {activeEvents.map((event) => (
                        <EventCard
                          key={event.id}
                          event={event}
                          zoneName={zoneNameById[event.zone_id]}
                          onFinalize={handleDeactivate}
                          onEdit={handleEdit}
                          onDelete={handleDelete}
                          saving={saving}
                        />
                      ))}
                    </div>
                  )}
                </section>

                {/* Expired events */}
                {expiredEvents.length > 0 && (
                  <section className="mb-8">
                    <h2 className="text-lg font-bold text-amber-600 flex items-center gap-2 mb-3">
                      <span className="w-2.5 h-2.5 bg-amber-500 rounded-full" />
                      Eventos Expirados
                      <span className="text-sm font-normal text-slate-500">({expiredEvents.length})</span>
                    </h2>
                    <div className="space-y-3">
                      {expiredEvents.map((event) => (
                        <EventCard
                          key={event.id}
                          event={event}
                          zoneName={zoneNameById[event.zone_id]}
                          onFinalize={handleDeactivate}
                          onEdit={handleEdit}
                          onDelete={handleDelete}
                          saving={saving}
                        />
                      ))}
                    </div>
                  </section>
                )}

                {/* Finalized events */}
                <section>
                  <button
                    onClick={() => setShowFinalized((v) => !v)}
                    className="flex items-center justify-between w-full text-left"
                  >
                    <h2 className="text-lg font-bold text-slate-600">
                      Eventos Finalizados ({finalizedEvents.length})
                    </h2>
                    <span className="text-slate-400 text-lg">{showFinalized ? '▼' : '▶'}</span>
                  </button>
                  {showFinalized && (
                    <div className="mt-3 space-y-2">
                      {finalizedEvents.length === 0 ? (
                        <div className="bg-white rounded-xl border border-slate-200 p-6 text-center text-slate-400 text-sm">
                          No hay eventos finalizados.
                        </div>
                      ) : (
                        finalizedEvents.map((event) => (
                          <EventCard
                            key={event.id}
                            event={event}
                            zoneName={zoneNameById[event.zone_id]}
                            onFinalize={handleDeactivate}
                            onEdit={handleEdit}
                            onDelete={handleDelete}
                            saving={saving}
                          />
                        ))
                      )}
                    </div>
                  )}
                </section>
              </>
            )}
          </>
        ) : (
          <FlowRestrictionSection />
        )}
      </main>

      {showForm && selectedDayId && (
        <EventFormModal
          initial={formInitial}
          eventDayId={selectedDayId}
          zones={zones}
          onSave={handleSave}
          onClose={closeForm}
          saving={saving}
        />
      )}
    </div>
  );
}
