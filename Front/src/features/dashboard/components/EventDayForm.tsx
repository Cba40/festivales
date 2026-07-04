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

const HOUR_OPTIONS = Array.from({ length: 24 }, (_, i) => ({
  value: i,
  label: `${i.toString().padStart(2, '0')}:00`,
}));

export function EventDayForm({ eventDay, onSave, onCancel, saving }: EventDayFormProps) {
  const isEditing = !!eventDay;

  const [date, setDate] = useState('');
  const [dayOfWeek, setDayOfWeek] = useState('');
  const [weather, setWeather] = useState('');
  const [headlinerArtist, setHeadlinerArtist] = useState('');
  const [expectedAttendance, setExpectedAttendance] = useState('');
  const [peakHourStart, setPeakHourStart] = useState('');
  const [peakHourEnd, setPeakHourEnd] = useState('');
  const [openingTime, setOpeningTime] = useState('');
  const [closingTime, setClosingTime] = useState('');
  const [notes, setNotes] = useState('');
  const [isActive, setIsActive] = useState(true);

  useEffect(() => {
    if (eventDay) {
      setDate(eventDay.date);
      setDayOfWeek(eventDay.day_of_week);
      setWeather(eventDay.weather ?? '');
      setHeadlinerArtist(eventDay.headliner_artist ?? '');
      setExpectedAttendance(eventDay.expected_attendance?.toString() ?? '');
      setPeakHourStart(eventDay.peak_hour_start?.toString() ?? '');
      setPeakHourEnd(eventDay.peak_hour_end?.toString() ?? '');
      setOpeningTime(eventDay.opening_time?.toString() ?? '');
      setClosingTime(eventDay.closing_time?.toString() ?? '');
      setNotes(eventDay.notes ?? '');
      setIsActive(eventDay.is_active);
    }
  }, [eventDay]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!date || !dayOfWeek) return;

    const payload: EventDayCreatePayload = {
      date,
      day_of_week: dayOfWeek,
      weather: weather || null,
      headliner_artist: headlinerArtist || null,
      expected_attendance: expectedAttendance ? parseInt(expectedAttendance, 10) : null,
      peak_hour_start: peakHourStart ? parseInt(peakHourStart, 10) : null,
      peak_hour_end: peakHourEnd ? parseInt(peakHourEnd, 10) : null,
      opening_time: openingTime ? parseInt(openingTime, 10) : null,
      closing_time: closingTime ? parseInt(closingTime, 10) : null,
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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Inicio hora pico</label>
          <select
            value={peakHourStart}
            onChange={(e) => setPeakHourStart(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Sin especificar</option>
            {HOUR_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Fin hora pico</label>
          <select
            value={peakHourEnd}
            onChange={(e) => setPeakHourEnd(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Sin especificar</option>
            {HOUR_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Apertura puertas</label>
          <select
            value={openingTime}
            onChange={(e) => setOpeningTime(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Sin especificar</option>
            {HOUR_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Cierre</label>
          <select
            value={closingTime}
            onChange={(e) => setClosingTime(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Sin especificar</option>
            {HOUR_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
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
