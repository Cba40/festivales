import { useState, useCallback, useMemo } from 'react';
import { Clock, AlertTriangle, CheckCircle } from 'lucide-react';
import { apiClient } from '../../core/api/client';
import { EVENT_ID } from './constants';

const TIME_FIELDS = [
  { key: 'entry_start_time', label: 'Apertura puertas', short: 'Entrada' },
  { key: 'entry_peak_start_time', label: 'Inicio pico ingreso', short: 'Pico ingreso' },
  { key: 'entry_peak_end_time', label: 'Fin pico ingreso', short: 'Fin ingreso' },
  { key: 'event_start_time', label: 'Inicio del show', short: 'Show' },
  { key: 'exit_peak_start_time', label: 'Inicio pico salida', short: 'Pico salida' },
  { key: 'exit_peak_end_time', label: 'Fin pico salida', short: 'Fin salida' },
  { key: 'event_end_time', label: 'Cierre total', short: 'Cierre' },
];

interface EventDayTimelineEditorProps {
  eventDayId?: string | null;
  initialTimes?: Record<string, string> | null;
  eventId?: string;
  onSaved?: () => void;
}

export function EventDayTimelineEditor({ eventDayId, initialTimes, eventId, onSaved }: EventDayTimelineEditorProps) {
  const eid = eventId || EVENT_ID;
  const [times, setTimes] = useState<Record<string, string>>(() => {
    if (initialTimes) return { ...initialTimes };
    const defaults: Record<string, string> = {};
    TIME_FIELDS.forEach(({ key }, i) => {
      defaults[key] = `${(8 + i * 2).toString().padStart(2, '0')}:00`;
    });
    return defaults;
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const errors = useMemo(() => {
    const result: string[] = [];
    for (let i = 1; i < TIME_FIELDS.length; i++) {
      const prev = times[TIME_FIELDS[i - 1].key];
      const curr = times[TIME_FIELDS[i].key];
      if (prev && curr && prev >= curr) {
        result.push(`${TIME_FIELDS[i - 1].label} (${prev}) debe ser anterior a ${TIME_FIELDS[i].label} (${curr})`);
      }
    }
    return result;
  }, [times]);

  const isValid = errors.length === 0;

  const hasInitialValues = initialTimes && Object.keys(initialTimes).length > 0;

  const timelinePct = useMemo(() => {
    const vals = TIME_FIELDS.map(({ key }) => {
      const t = times[key];
      if (!t) return 0;
      const [h, m] = t.split(':').map(Number);
      return (h * 60 + m) / (24 * 60) * 100;
    });
    return vals;
  }, [times]);

  const handleTimeChange = useCallback((key: string, value: string) => {
    setTimes(prev => ({ ...prev, [key]: value }));
    setSuccess(false);
    setError(null);
  }, []);

  const handleSave = useCallback(async () => {
    if (!isValid) return;
    setSaving(true);
    setError(null);
    setSuccess(false);
    const id = eventDayId || 'new';
    const isNew = !eventDayId;
    try {
      const base = `/events/${eid}/event-days`;
      const payload = { ...times, is_active: true };
      if (isNew) {
        await apiClient.post(base, {
          ...payload,
          date: new Date().toISOString().split('T')[0],
          day_of_week: new Date().toLocaleDateString('es-AR', { weekday: 'long' }),
        });
      } else {
        await apiClient.put(`${base}/${id}`, payload);
      }
      setSuccess(true);
      onSaved?.();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al guardar');
    } finally {
      setSaving(false);
    }
  }, [times, isValid, eventDayId, eid, onSaved]);

  return (
    <div className="space-y-5">
      {success && (
        <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-700">
          <CheckCircle className="w-4 h-4" /> Jornada guardada correctamente
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="relative pt-8 pb-4">
        <div className="absolute top-0 left-0 right-0 h-2 bg-slate-200 rounded-full">
          <div className="absolute inset-0 flex">
            {timelinePct.slice(0, -1).map((pct, i) => (
              <div
                key={i}
                className="h-full bg-blue-500"
                style={{ width: `${timelinePct[i + 1] - pct}%`, marginLeft: i === 0 ? `${pct}%` : undefined }}
              />
            ))}
          </div>
        </div>
        <div className="flex justify-between relative" style={{ height: 4 }}>
          {timelinePct.map((pct, i) => (
            <div
              key={i}
              className="absolute w-3 h-3 bg-blue-600 rounded-full -translate-x-1/2 -translate-y-1/2 ring-2 ring-white"
              style={{ left: `${pct}%`, top: 0 }}
              title={TIME_FIELDS[i].label}
            />
          ))}
        </div>
        <div className="flex justify-between mt-2">
          {TIME_FIELDS.map(({ short }, i) => (
            <span key={i} className="text-[10px] text-slate-500 text-center truncate" style={{ width: `${100 / 7}%` }}>
              {short}
            </span>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {TIME_FIELDS.map(({ key, label }) => (
          <div key={key}>
            <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>
            <input
              type="time"
              value={times[key] || ''}
              onChange={(e) => handleTimeChange(key, e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        ))}
      </div>

      {errors.length > 0 && (
        <div className="space-y-1">
          {errors.map((err, i) => (
            <div key={i} className="flex items-start gap-2 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
              <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              <span>{err}</span>
            </div>
          ))}
        </div>
      )}

      {errors.length === 0 && (
        <div className="flex items-center gap-2 p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700">
          <Clock className="w-3.5 h-3.5 shrink-0" />
          Orden temporal correcto
        </div>
      )}

      <div className="flex justify-end gap-3">
        <button
          onClick={handleSave}
          disabled={!isValid || saving}
          className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {saving ? 'Guardando...' : hasInitialValues ? 'Actualizar jornada' : 'Crear jornada'}
        </button>
      </div>
    </div>
  );
}
