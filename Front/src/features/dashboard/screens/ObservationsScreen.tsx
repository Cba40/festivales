import { useEffect, useCallback, useMemo, useState } from 'react';
import { RefreshCw, Plus } from 'lucide-react';
import { EVENT_ID } from '@/components/context-engine/constants';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import { useOperationalObservations } from '@/hooks/useOperationalObservations';
import { Button, Card } from '@/features/dashboard/components/ui';

const SOURCES = [
  { value: 'manual', label: 'Manual' },
  { value: 'sensor', label: 'Sensor' },
  { value: 'official_report', label: 'Reporte oficial' },
];

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

function formatZoneId(zoneId: string): string {
  return zoneId.length >= 8 ? `${zoneId.slice(0, 8)}…` : zoneId;
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

export function ObservationsScreen() {
  const { observations, isLoading, isSubmitting, error, fetchObservations, createObservation } =
    useOperationalObservations();

  const [zones, setZones] = useState<ZoneInfo[]>([]);
  const [eventDays, setEventDays] = useState<EventDaySummary[]>([]);

  const [zoneId, setZoneId] = useState('');
  const [eventDayId, setEventDayId] = useState('');
  const [timestamp, setTimestamp] = useState(
    () => new Date().toISOString().slice(0, 16)
  );
  const [observedDensity, setObservedDensity] = useState('');
  const [observerId, setObserverId] = useState('');
  const [source, setSource] = useState('manual');
  const [notas, setNotas] = useState('');
  const [formMessage, setFormMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    fetchObservations();
  }, [fetchObservations]);

  useEffect(() => {
    let cancelled = false;
    apiClient
      .get<ZoneInfo[]>(endpoints.zones.list(EVENT_ID))
      .then((res) => {
        if (!cancelled) setZones(res.data ?? []);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    apiClient
      .get<EventDaySummary[]>(endpoints.eventDays.list(EVENT_ID))
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
  }, []);

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
      observer_id: observerId.trim() !== '' ? observerId.trim() : undefined,
      source,
      ...(metadataPayload ? { metadata: metadataPayload } : {}),
    });

    if (result) {
      setFormMessage('Observación registrada correctamente.');
      setObservedDensity('');
      setObserverId('');
      setNotas('');
      if (selectedDay) setTimestamp(defaultTimestampForDay(selectedDay));
    } else if (error && /outside the operational range/i.test(error)) {
      setFormError(
        'La hora seleccionada está fuera del rango operativo de la jornada elegida. Por favor, ajustá la hora o seleccioná otra jornada.'
      );
    }
  }, [eventDayId, zoneId, timestamp, observedDensity, observerId, source, notas, createObservation, error, timeInRange, selectedDay]);

  return (
    <main className="max-w-5xl mx-auto space-y-6">
      <div className="flex justify-end">
        <button
          onClick={() => { fetchObservations(); }}
          disabled={isLoading}
          className="flex items-center gap-1 text-sm px-3 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-600 font-medium disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          {isLoading ? 'Cargando...' : 'Actualizar'}
        </button>
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
              <span className="text-slate-700 font-medium">Observador (opcional)</span>
              <input
                type="text"
                value={observerId}
                onChange={(e) => setObserverId(e.target.value)}
                placeholder="ID del observador"
                className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
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
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="px-5 py-2 font-medium">Fecha / Hora</th>
                <th className="px-5 py-2 font-medium">Zona</th>
                <th className="px-5 py-2 font-medium">Densidad</th>
                <th className="px-5 py-2 font-medium">Observador</th>
                <th className="px-5 py-2 font-medium">Fuente</th>
              </tr>
            </thead>
            <tbody>
              {observations.length === 0 && !isLoading && (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-slate-400 italic">
                    Sin observaciones registradas todavía.
                  </td>
                </tr>
              )}
              {observations.map((obs) => {
                const zona = zonesById[obs.zone_id];
                return (
                  <tr key={obs.id} className="border-b border-slate-100">
                    <td className="px-5 py-2 text-slate-600">{formatTimestamp(obs.timestamp)}</td>
                    <td className="px-5 py-2 text-slate-700">
                      {zona ? zona.name : formatZoneId(obs.zone_id)}
                    </td>
                    <td className="px-5 py-2 text-slate-700">{obs.observed_density}</td>
                    <td className="px-5 py-2 text-slate-600">{obs.observer_id || '—'}</td>
                    <td className="px-5 py-2 text-slate-600">{obs.source}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </main>
  );
}