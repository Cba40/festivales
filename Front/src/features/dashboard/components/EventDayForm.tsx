import { useState, useEffect } from 'react';
import type { EventDay, EventDayCreatePayload } from '../types';

interface EventDayFormProps {
  eventDay?: EventDay | null;
  onSave: (payload: EventDayCreatePayload) => Promise<void>;
  onCancel: () => void;
  saving: boolean;
}

const DAYS_OF_WEEK = [
  'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo',
];

const WEATHER_OPTIONS = [
  { value: '', label: 'Sin especificar' },
  { value: 'soleado', label: '☀️ Soleado' },
  { value: 'nublado', label: '☁️ Nublado' },
  { value: 'lluvioso', label: '🌧️ Lluvioso' },
  { value: 'tormenta', label: '⛈️ Tormenta' },
];

const TIME_LABELS: { key: keyof EventDayCreatePayload; label: string; hint: string }[] = [
  { key: 'entry_start_time', label: 'Apertura de puertas', hint: 'Comienza el ingreso del público' },
  { key: 'entry_peak_start_time', label: 'Inicio pico de ingreso', hint: 'Mayor caudal de entrada' },
  { key: 'entry_peak_end_time', label: 'Fin pico de ingreso', hint: 'Disminuye el caudal de entrada' },
  { key: 'event_start_time', label: 'Inicio del show', hint: 'Comienza el evento principal' },
  { key: 'exit_peak_start_time', label: 'Inicio pico de salida', hint: 'Comienza la salida masiva' },
  { key: 'exit_peak_end_time', label: 'Fin pico de salida', hint: 'Disminuye la salida masiva' },
  { key: 'event_end_time', label: 'Cierre total', hint: 'Finaliza la jornada' },
];

function isValidTimeOrder(times: Record<string, string>): { valid: boolean; error: string | null } {
  const order: (keyof EventDayCreatePayload)[] = [
    'entry_start_time',
    'entry_peak_start_time',
    'entry_peak_end_time',
    'event_start_time',
    'exit_peak_start_time',
    'exit_peak_end_time',
    'event_end_time',
  ];

  for (let i = 0; i < order.length - 1; i++) {
    const a = times[order[i]];
    const b = times[order[i + 1]];
    if (!a || !b) {
      return { valid: false, error: 'Todos los horarios son obligatorios' };
    }
    if (a >= b) {
      const prevLabel = TIME_LABELS.find(t => t.key === order[i])?.label ?? order[i];
      const nextLabel = TIME_LABELS.find(t => t.key === order[i + 1])?.label ?? order[i + 1];
      return {
        valid: false,
        error: `"${prevLabel}" (${a}) debe ser anterior a "${nextLabel}" (${b})`,
      };
    }
  }

  return { valid: true, error: null };
}

export function EventDayForm({ eventDay, onSave, onCancel, saving }: EventDayFormProps) {
  const isEditing = !!eventDay;

  const [date, setDate] = useState('');
  const [dayOfWeek, setDayOfWeek] = useState('');
  const [weather, setWeather] = useState('');
  const [headlinerArtist, setHeadlinerArtist] = useState('');
  const [expectedAttendance, setExpectedAttendance] = useState('');
  const [notes, setNotes] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [validationError, setValidationError] = useState<string | null>(null);

  const [entryStartTime, setEntryStartTime] = useState('');
  const [entryPeakStartTime, setEntryPeakStartTime] = useState('');
  const [entryPeakEndTime, setEntryPeakEndTime] = useState('');
  const [eventStartTime, setEventStartTime] = useState('');
  const [exitPeakStartTime, setExitPeakStartTime] = useState('');
  const [exitPeakEndTime, setExitPeakEndTime] = useState('');
  const [eventEndTime, setEventEndTime] = useState('');

  useEffect(() => {
    if (eventDay) {
      setDate(eventDay.date);
      setDayOfWeek(eventDay.day_of_week);
      setWeather(eventDay.weather ?? '');
      setHeadlinerArtist(eventDay.headliner_artist ?? '');
      setExpectedAttendance(eventDay.expected_attendance?.toString() ?? '');
      setEntryStartTime(eventDay.entry_start_time ?? '');
      setEntryPeakStartTime(eventDay.entry_peak_start_time ?? '');
      setEntryPeakEndTime(eventDay.entry_peak_end_time ?? '');
      setEventStartTime(eventDay.event_start_time ?? '');
      setExitPeakStartTime(eventDay.exit_peak_start_time ?? '');
      setExitPeakEndTime(eventDay.exit_peak_end_time ?? '');
      setEventEndTime(eventDay.event_end_time ?? '');
      setNotes(eventDay.notes ?? '');
      setIsActive(eventDay.is_active);
    }
  }, [eventDay]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);
    if (!date || !dayOfWeek) return;

    const times = {
      entry_start_time: entryStartTime,
      entry_peak_start_time: entryPeakStartTime,
      entry_peak_end_time: entryPeakEndTime,
      event_start_time: eventStartTime,
      exit_peak_start_time: exitPeakStartTime,
      exit_peak_end_time: exitPeakEndTime,
      event_end_time: eventEndTime,
    };

    const timeValidation = isValidTimeOrder(times);
    if (!timeValidation.valid) {
      setValidationError(timeValidation.error);
      return;
    }

    const payload: EventDayCreatePayload = {
      date,
      day_of_week: dayOfWeek,
      ...times,
      weather: weather || null,
      headliner_artist: headlinerArtist || null,
      expected_attendance: expectedAttendance ? parseInt(expectedAttendance, 10) : null,
      notes: notes || null,
      is_active: isActive,
    };

    if (isEditing && eventDay) {
      const changed = Object.fromEntries(
        Object.entries(payload).filter(
          ([key, value]) => value !== (eventDay as any)[key]
        )
      );
      if (Object.keys(changed).length === 0) return;
      await onSave(changed as EventDayCreatePayload);
    } else {
      await onSave(payload);
    }
  };

  const timeSetters: Record<string, React.Dispatch<React.SetStateAction<string>>> = {
    entry_start_time: setEntryStartTime,
    entry_peak_start_time: setEntryPeakStartTime,
    entry_peak_end_time: setEntryPeakEndTime,
    event_start_time: setEventStartTime,
    exit_peak_start_time: setExitPeakStartTime,
    exit_peak_end_time: setExitPeakEndTime,
    event_end_time: setEventEndTime,
  };

  const timeValues: Record<string, string> = {
    entry_start_time: entryStartTime,
    entry_peak_start_time: entryPeakStartTime,
    entry_peak_end_time: entryPeakEndTime,
    event_start_time: eventStartTime,
    exit_peak_start_time: exitPeakStartTime,
    exit_peak_end_time: exitPeakEndTime,
    event_end_time: eventEndTime,
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Fecha *</label>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Día de la semana *</label>
          <select
            value={dayOfWeek}
            onChange={(e) => setDayOfWeek(e.target.value)}
            required
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Seleccionar...</option>
            {DAYS_OF_WEEK.map((d) => (
              <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Clima</label>
          <select
            value={weather}
            onChange={(e) => setWeather(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {WEATHER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Artista principal</label>
          <input
            type="text"
            value={headlinerArtist}
            onChange={(e) => setHeadlinerArtist(e.target.value)}
            placeholder="Ej: Los Auténticos Decadentes"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Convocatoria estimada</label>
          <input
            type="number"
            min={0}
            value={expectedAttendance}
            onChange={(e) => setExpectedAttendance(e.target.value)}
            placeholder="Ej: 50000"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center gap-3 pt-6">
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-slate-300 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600" />
          </label>
          <span className="text-sm font-medium text-slate-700">Día activo</span>
        </div>
      </div>

      {validationError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {validationError}
        </div>
      )}

      <div className="border-t border-slate-200 pt-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Línea de tiempo del evento</h3>
        <p className="text-xs text-slate-500 mb-3">
          Los horarios deben respetar el orden cronológico. Todos los campos son obligatorios.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {TIME_LABELS.map(({ key, label, hint }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-slate-700 mb-1">{label} *</label>
              <input
                type="time"
                value={timeValues[key]}
                onChange={(e) => timeSetters[key](e.target.value)}
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-[10px] text-slate-400 mt-0.5">{hint}</p>
            </div>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Notas</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="Información adicional sobre este día..."
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={saving || !date || !dayOfWeek}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {saving ? 'Guardando...' : isEditing ? 'Actualizar' : 'Crear día'}
        </button>
      </div>
    </form>
  );
}
