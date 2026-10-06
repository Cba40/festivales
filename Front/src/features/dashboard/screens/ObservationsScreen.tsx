import { useEffect, useCallback, useMemo, useState } from 'react';
import { Pencil, Plus } from 'lucide-react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import { useAppStore } from '@/core/state/store';
import { useOperationalObservations } from '@/hooks/useOperationalObservations';
import { Badge, Button, Card, RefreshButton } from '@/features/dashboard/components/ui';
import { ObservationEditModal } from '@/features/dashboard/components/ObservationEditModal';
import { truncateId } from '@/features/dashboard/utils/format';
import type {
  OperationalObservationDTO,
  OperationalObservationUpdatePayload,
} from '@/features/dashboard/types';

const SOURCES = [
  { value: 'manual', label: 'Manual' },
  { value: 'sensor', label: 'Sensor' },
  { value: 'official_report', label: 'Reporte oficial' },
];

/**
 * Nombre del observador para mostrar en el formulario y en la tabla.
 *
 * Antes el formulario tenía un input de texto donde el operador escribía un ID a
 * mano, y la tabla mostraba el UUID crudo. El `observer_id` real lo inyecta el
 * servidor desde el token (`operational_observations.py:43`), así que lo que el
 * operador escribía se descartaba: era un campo que aparente tener efecto y no
 * lo tenia.
 */
function observerLabel(observerName?: string | null): string {
  return observerName?.trim() || 'Desconocido';
}

interface ZoneInfo {
  id: string;
  name: string;
  type: string;
}

interface EventDaySummary {
  id: string;
  date: string;
  is_active: boolean;
  operational_start_min: number;
  operational_end_min: number;
}

function formatTimestamp(value: string): string {
  const d = new Date(value);
  return d.toLocaleString('es-AR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function pad2(n: number): string {
  return n.toString().padStart(2, '0');
}

function formatOperationalTime(min: number): string {
  return `${pad2(Math.floor(min / 60))}:${pad2(min % 60)}`;
}

function minutesInDay(value: string): number {
  const [, time] = value.split('T');
  if (!time) return 0;
  const [h, m] = time.split(':').map(Number);
  return (h || 0) * 60 + (m || 0);
}

function dayDateString(value: string): string {
  return value.slice(0, 10);
}

function nowLocalInput(): string {
  const now = new Date();
  return (
    `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}` +
    `T${pad2(now.getHours())}:${pad2(now.getMinutes())}`
  );
}

function isWithinEventDay(day: EventDaySummary | undefined, value: string): boolean {
  if (!day || !value) return false;
  const daysDiff = Math.round(
    (new Date(`${dayDateString(value)}T00:00:00`).getTime() -
      new Date(`${day.date}T00:00:00`).getTime()) /
      86400000
  );
  const currentMin = daysDiff * 1440 + minutesInDay(value);
  return currentMin >= day.operational_start_min && currentMin < day.operational_end_min;
}

function defaultTimestampForDay(day: EventDaySummary): string {
  const nowLocal = nowLocalInput();
  if (isWithinEventDay(day, nowLocal)) return nowLocal;
  return `${day.date}T${formatOperationalTime(day.operational_start_min)}`;
}

/**
 * Warnings de calidad que escribe el backend en `metadata.warnings`
 * (app/crud/operational_observation.py). Se muestran porque son el aviso de
 * "esto puede estar mal": hasta ahora la tabla los escondía y el inspector no
 * tenía forma de saber cuáles de sus conteos habían sido marcados.
 */
const WARNING_LABELS: Record<string, string> = {
  variacion_extrema: 'Variación extrema',
  posible_error_tipeo: 'Posible error de tipeo',
};

function warningsDe(obs: OperationalObservationDTO): string[] {
  const raw = obs.metadata?.warnings;
  return Array.isArray(raw) ? raw.filter((w): w is string => typeof w === 'string') : [];
}

function formatCorrectionDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function ObservationsScreen() {
  // Identidad del operador, para mostrar en solo lectura quien queda registrada
  // como observador. No se manda: el `observer_id` lo pone el servidor desde el
  // token. Esto es solo confianza de que el sistema sabe quien es.
  const user = useAppStore((s) => s.auth.user);
  const observerDisplayName = user?.full_name || user?.username || 'tu usuario';

  // Evento activo del store global (`useActiveEvent`), no `VITE_EVENT_ID`.
  const eventId = useAppStore((s) => s.activeEventId);

  const {
    observations,
    isLoading,
    isSubmitting,
    isUpdating,
    error,
    fetchObservations,
    createObservation,
    updateObservation,
  } = useOperationalObservations();

  const [zones, setZones] = useState<ZoneInfo[]>([]);
  const [eventDays, setEventDays] = useState<EventDaySummary[]>([]);

  const [zoneId, setZoneId] = useState('');
  const [eventDayId, setEventDayId] = useState('');
  const [timestamp, setTimestamp] = useState(
    () => new Date().toISOString().slice(0, 16)
  );
  const [observedDensity, setObservedDensity] = useState('');
  const [source, setSource] = useState('manual');
  const [notas, setNotas] = useState('');
  const [formMessage, setFormMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [editing, setEditing] = useState<OperationalObservationDTO | null>(null);
  const [editError, setEditError] = useState<string | null>(null);

  useEffect(() => {
    fetchObservations();
  }, [fetchObservations]);

  // `eventId` en las deps: hasta que resuelve no hay catálogo que pedir, y cuando
  // resuelve hay que pedirlo para ese evento.
  useEffect(() => {
    if (!eventId) return;
    let cancelled = false;
    apiClient
      .get<ZoneInfo[]>(endpoints.zones.list(eventId))
      .then((res) => {
        if (!cancelled) setZones(res.data ?? []);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [eventId]);

  useEffect(() => {
    if (!eventId) return;
    let cancelled = false;
    apiClient
      .get<EventDaySummary[]>(endpoints.eventDays.list(eventId))
      .then((res) => {
        if (cancelled) return;
        setEventDays(res.data ?? []);
        const active = (res.data ?? []).find((d) => d.is_active);
        if (active) {
          setEventDayId(active.id);
          setTimestamp(defaultTimestampForDay(active));
        } else if ((res.data ?? []).length > 0) {
          const first = (res.data ?? [])[0];
          setEventDayId(first.id);
          setTimestamp(defaultTimestampForDay(first));
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [eventId]);

  const handleEventDayChange = (value: string) => {
    setEventDayId(value);
    const day = eventDays.find((d) => d.id === value);
    if (day) setTimestamp(defaultTimestampForDay(day));
  };

  const zonesById = useMemo(() => {
    const map: Record<string, ZoneInfo> = {};
    for (const z of zones) map[z.id] = z;
    return map;
  }, [zones]);

  const selectedDay = useMemo(
    () => eventDays.find((d) => d.id === eventDayId),
    [eventDays, eventDayId]
  );
  const timeInRange = isWithinEventDay(selectedDay, timestamp);

  const handleSubmit = useCallback(async () => {
    if (!eventDayId || !zoneId || !timestamp || observedDensity === '') {
      setFormError('Completá zona, jornada, fecha/hora y densidad observada.');
      return;
    }
    const density = Number(observedDensity);
    if (!Number.isFinite(density) || density < 0) {
      setFormError('La densidad observada debe ser un número mayor o igual a 0.');
      return;
    }
    if (!timeInRange && selectedDay) {
      setFormError(
        `La hora seleccionada está fuera del rango operativo de la jornada elegida ` +
          `(${formatOperationalTime(selectedDay.operational_start_min)} a ` +
          `${formatOperationalTime(selectedDay.operational_end_min)}). Por favor, ajustá la hora o seleccioná otra jornada.`
      );
      return;
    }

    let metadataPayload: Record<string, unknown> | undefined;
    if (notas.trim() !== '') {
      metadataPayload = { notas: notas.trim() };
    }

    setFormMessage(null);
    setFormError(null);

    const result = await createObservation({
      event_day_id: eventDayId,
      zone_id: zoneId,
      timestamp: new Date(timestamp).toISOString(),
      observed_density: density,
      // Sin `observer_id`: lo inyecta el servidor desde el token.
      source,
      ...(metadataPayload ? { metadata: metadataPayload } : {}),
    });

    if (result) {
      setFormMessage('Observación registrada correctamente.');
      setObservedDensity('');
      setNotas('');
      if (selectedDay) setTimestamp(defaultTimestampForDay(selectedDay));
    } else if (error && /outside the operational range/i.test(error)) {
      setFormError(
        'La hora seleccionada está fuera del rango operativo de la jornada elegida. Por favor, ajustá la hora o seleccioná otra jornada.'
      );
    }
  }, [eventDayId, zoneId, timestamp, observedDensity, source, notas, createObservation, error, timeInRange, selectedDay]);

  const handleSaveEdit = useCallback(
    async (
      obs: OperationalObservationDTO,
      payload: Required<Pick<OperationalObservationUpdatePayload, 'observed_density' | 'source'>> &
        OperationalObservationUpdatePayload
    ) => {
      setEditError(null);
      const saved = await updateObservation(obs.id, payload);
      if (saved) {
        setEditing(null);
        setFormMessage('Observación corregida correctamente.');
      } else {
        setEditError(
          'No se pudo guardar la corrección. Revisá los datos e intentá de nuevo.'
        );
      }
    },
    [updateObservation]
  );

  return (
    <main className="max-w-5xl mx-auto space-y-6">
      <div className="flex justify-end">
        <RefreshButton onClick={() => void fetchObservations()} loading={isLoading} />
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
      )}

      <Card variant="standard">
        <h2 className="font-bold text-slate-800 mb-4">Registrar Observación</h2>
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <label className="block text-sm">
              <span className="text-slate-700 font-medium">Zona</span>
              <select
                value={zoneId}
                onChange={(e) => setZoneId(e.target.value)}
                className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">Seleccionar zona…</option>
                {zones.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.name} ({z.type})
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="text-slate-700 font-medium">Jornada</span>
              <select
                value={eventDayId}
                onChange={(e) => handleEventDayChange(e.target.value)}
                className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">Seleccionar jornada…</option>
                {eventDays.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.date} {d.is_active ? '(Hoy)' : ''}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="text-slate-700 font-medium">Fecha y hora</span>
              <input
                type="datetime-local"
                value={timestamp}
                onChange={(e) => setTimestamp(e.target.value)}
                className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
              {selectedDay && !timeInRange && (
                <span className="block mt-1 text-xs text-red-600">
                  La hora está fuera del rango operativo de la jornada (
                  {formatOperationalTime(selectedDay.operational_start_min)} a{' '}
                  {formatOperationalTime(selectedDay.operational_end_min)}).
                </span>
              )}
            </label>
            <label className="block text-sm">
              <span className="text-slate-700 font-medium">Densidad observada</span>
              <input
                type="number"
                min={0}
                value={observedDensity}
                onChange={(e) => setObservedDensity(e.target.value)}
                placeholder="0"
                className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </label>
            <label className="block text-sm">
              <span className="text-slate-700 font-medium">Observador</span>
              {/* Solo lectura y no un input: el `observer_id` lo inyecta el
                  servidor desde el token, asi que un campo editable seria una
                  mentira. Mostrar el nombre confirma al operador que el sistema
                  sabe quien es, que era el problema: antes habia un input que
                  pedia un ID a mano y el valor se descartaba. */}
              <input
                type="text"
                value={observerDisplayName}
                readOnly
                tabIndex={-1}
                aria-readonly="true"
                title="Se completa automáticamente con tu usuario. No se puede modificar."
                className="mt-1 w-full px-3 py-2 border border-slate-200 bg-slate-50 rounded-lg text-sm text-slate-600 cursor-not-allowed"
              />
              <span className="mt-1 block text-xs text-slate-400">
                Registrado automáticamente desde tu sesión. No se puede modificar.
              </span>
            </label>
            <label className="block text-sm">
              <span className="text-slate-700 font-medium">Fuente</span>
              <select
                value={source}
                onChange={(e) => setSource(e.target.value)}
                className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                {SOURCES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Notas adicionales (opcional)
            </label>
            <input
              type="text"
              value={notas}
              onChange={(e) => setNotas(e.target.value)}
              placeholder="Ej: Zona con mucha afluencia por evento cercano"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              disabled={isSubmitting}
            />
          </div>

          {formError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{formError}</div>
          )}
          {formMessage && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">{formMessage}</div>
          )}

          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || (!!selectedDay && !timeInRange)}
          >
            <Plus className="w-4 h-4" />
            {isSubmitting ? 'Registrando...' : 'Registrar Observación'}
          </Button>
        </div>
      </Card>

      <Card variant="standard">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-slate-800">Observaciones recientes ({observations.length})</h2>
        </div>
        {editError && (
          <div className="p-3 mb-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {editError}
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="px-5 py-2 font-medium">Fecha / Hora</th>
                <th className="px-5 py-2 font-medium">Zona</th>
                <th className="px-5 py-2 font-medium">Densidad</th>
                <th className="px-5 py-2 font-medium">Observador</th>
                <th className="px-5 py-2 font-medium">Fuente</th>
                <th className="px-5 py-2 font-medium text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {observations.length === 0 && !isLoading && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-slate-400 italic">
                    Sin observaciones registradas todavía.
                  </td>
                </tr>
              )}
              {observations.map((obs) => {
                const zona = zonesById[obs.zone_id];
                const warnings = warningsDe(obs);
                return (
                  <tr key={obs.id} className="border-b border-slate-100 align-top">
                    <td className="px-5 py-2 text-slate-600">{formatTimestamp(obs.timestamp)}</td>
                    <td className="px-5 py-2 text-slate-700">
                      {zona ? zona.name : truncateId(obs.zone_id)}
                    </td>
                    <td className="px-5 py-2 text-slate-700">
                      <div>{obs.observed_density}</div>
                      {warnings.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {warnings.map((w) => (
                            <Badge key={w} variant={w === 'variacion_extrema' ? 'warning' : 'error'}>
                              {WARNING_LABELS[w] ?? w}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </td>
                    {/* Nombre del observador, no el UUID. Y si la observación
                        tiene alertas de calidad, se resalta: el nombre es
                        justamente lo que el administrador necesita para saber a
                        quién pedir la corrección. */}
                    <td className="px-5 py-2">
                      {warnings.length > 0 ? (
                        <span className="inline-flex items-center gap-1 font-semibold text-amber-700 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5">
                          {observerLabel(obs.observer_name)}
                        </span>
                      ) : (
                        <span className="text-slate-600">
                          {observerLabel(obs.observer_name)}
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-2 text-slate-600">
                      <div>{obs.source}</div>
                      {obs.corrected_by && (
                        <div className="mt-1" title={`${obs.corrected_by}${
                          obs.corrected_at ? ` · ${formatCorrectionDate(obs.corrected_at)}` : ''
                        }`}>
                          <Badge variant="info">Corregido</Badge>
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-2 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditError(null);
                          setEditing(obs);
                        }}
                        disabled={isUpdating}
                      >
                        <Pencil className="w-3 h-3" />
                        Editar
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <ObservationEditModal
        observation={editing}
        isSaving={isUpdating}
        onSave={handleSaveEdit}
        onClose={() => setEditing(null)}
      />
    </main>
  );
}