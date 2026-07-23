import { useState, useEffect, useMemo } from 'react';
import { EventDayPhaseEditor, validatePhases } from './EventDayPhaseEditor';
import { useOperationalProfiles } from '../hooks/useOperationalProfiles';
import { useAttendanceLevels } from '../hooks/useAttendanceLevels';
import { useOperationalPhases } from '../hooks/useOperationalPhases';
import type {
  EventDay, EventDayCreatePayload, EventDayPhaseCreatePayload,
} from '../types';

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
  { value: 'soleado', label: 'Soleado' },
  { value: 'nublado', label: 'Nublado' },
  { value: 'lluvioso', label: 'Lluvioso' },
  { value: 'tormenta', label: 'Tormenta' },
];

function minutesToTimeStr(min: number): string {
  const h = Math.floor(min / 60).toString().padStart(2, '0');
  const m = (min % 60).toString().padStart(2, '0');
  return `${h}:${m}`;
}

function timeStrToMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number);
  return h * 60 + m;
}

export function EventDayForm({ eventDay, onSave, onCancel, saving }: EventDayFormProps) {
  const isEditing = !!eventDay;

  const [date, setDate] = useState('');
  const [dayOfWeek, setDayOfWeek] = useState('');
  const [weather, setWeather] = useState('');
  const [headlinerArtist, setHeadlinerArtist] = useState('');
  const [notes, setNotes] = useState('');
  const [isActive, setIsActive] = useState(true);

  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [selectedLevelId, setSelectedLevelId] = useState('');

  const { profiles, loading: profilesLoading } = useOperationalProfiles();
  const { levels, loading: levelsLoading } = useAttendanceLevels();
  const { phases: operationalPhases, loading: operationalPhasesLoading } = useOperationalPhases(selectedProfileId);

  const [operationalStartStr, setOperationalStartStr] = useState('');
  const [operationalEndStr, setOperationalEndStr] = useState('');

  const [eventDayPhases, setEventDayPhases] = useState<EventDayPhaseCreatePayload[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (eventDay) {
      setDate(eventDay.date);
      setDayOfWeek(eventDay.day_of_week);
      setWeather(eventDay.weather ?? '');
      setHeadlinerArtist(eventDay.headliner_artist ?? '');
      setSelectedProfileId(eventDay.operational_profile_id);
      setSelectedLevelId(eventDay.attendance_level_id);
      setOperationalStartStr(minutesToTimeStr(eventDay.operational_start_min));
      setOperationalEndStr(minutesToTimeStr(eventDay.operational_end_min));
      setNotes(eventDay.notes ?? '');
      setIsActive(eventDay.is_active);
      if (eventDay.phases && eventDay.phases.length > 0) {
        setEventDayPhases(
          eventDay.phases.map((p) => ({
            operational_phase_id: p.operational_phase_id,
            start_min: p.start_min,
            end_min: p.end_min,
          })),
        );
      }
    }
  }, [eventDay]);

  const operationalStartMin = useMemo(
    () => (operationalStartStr ? timeStrToMinutes(operationalStartStr) : 0),
    [operationalStartStr],
  );
  const operationalEndMin = useMemo(
    () => (operationalEndStr ? timeStrToMinutes(operationalEndStr) : 0),
    [operationalEndStr],
  );

  const currentPhaseErrors = useMemo(
    () => validatePhases(eventDayPhases, operationalStartMin, operationalEndMin),
    [eventDayPhases, operationalStartMin, operationalEndMin],
  );

  const selectedLevel = levels.find((l) => l.id === selectedLevelId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!date || !dayOfWeek || !selectedProfileId || !selectedLevelId) {
      setValidationError('Completá todos los campos obligatorios');
      return;
    }
    if (!operationalStartStr || !operationalEndStr) {
      setValidationError('La ventana operativa es obligatoria');
      return;
    }
    if (operationalEndMin <= operationalStartMin) {
      setValidationError('El fin de jornada debe ser posterior al inicio');
      return;
    }
    if (eventDayPhases.length === 0) {
      setValidationError('Debe haber al menos una fase en la jornada');
      return;
    }
    if (currentPhaseErrors.length > 0) {
      setValidationError('Corregí los errores en las fases antes de guardar');
      return;
    }

    const payload: EventDayCreatePayload = {
      date,
      day_of_week: dayOfWeek,
      operational_profile_id: selectedProfileId,
      attendance_level_id: selectedLevelId,
      operational_start_min: operationalStartMin,
      operational_end_min: operationalEndMin,
      phases: eventDayPhases,
      weather: weather || null,
      headliner_artist: headlinerArtist || null,
      notes: notes || null,
      is_active: isActive,
    };

    await onSave(payload);
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

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-slate-700 mb-1">Perfil operativo *</label>
          <select
            value={selectedProfileId}
            onChange={(e) => { setSelectedProfileId(e.target.value); setEventDayPhases([]); }}
            required
            disabled={profilesLoading}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <option value="">{profilesLoading ? 'Cargando perfiles...' : 'Seleccionar perfil...'}</option>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-slate-700 mb-1">Nivel de asistencia *</label>
          <select
            value={selectedLevelId}
            onChange={(e) => setSelectedLevelId(e.target.value)}
            required
            disabled={levelsLoading}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <option value="">{levelsLoading ? 'Cargando niveles...' : 'Seleccionar nivel...'}</option>
            {levels.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name} ({l.min_people.toLocaleString()}—{l.max_people ? l.max_people.toLocaleString() : '∞'}) ×{l.global_multiplier}
              </option>
            ))}
          </select>
          {selectedLevel && (
            <p className="text-[10px] text-slate-400 mt-0.5">
              Multiplicador global: {selectedLevel.global_multiplier} — rango: {selectedLevel.min_people.toLocaleString()} a{' '}
              {selectedLevel.max_people ? selectedLevel.max_people.toLocaleString() : 'sin límite'} personas
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Inicio de jornada territorial *</label>
          <input
            type="time"
            value={operationalStartStr}
            onChange={(e) => setOperationalStartStr(e.target.value)}
            required
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-[10px] text-slate-400 mt-0.5">Ej: 08:00 = 480 min desde medianoche</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Fin de jornada territorial *</label>
          <input
            type="time"
            value={operationalEndStr}
            onChange={(e) => setOperationalEndStr(e.target.value)}
            required
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-[10px] text-slate-400 mt-0.5">Ej: 06:00 (+1 día) = 1800 min (&gt;1440 cruza medianoche)</p>
        </div>
      </div>

      {selectedProfileId && (
        <div className="border-t border-slate-200 pt-4">
          {operationalPhasesLoading ? (
            <div className="text-xs text-slate-400">Cargando fases del perfil...</div>
          ) : (
            <EventDayPhaseEditor
              phases={eventDayPhases}
              operationalPhases={operationalPhases}
              operationalStartMin={operationalStartMin}
              operationalEndMin={operationalEndMin}
              onChange={setEventDayPhases}
              errors={[]}
            />
          )}
        </div>
      )}

      <div className="border-t border-slate-200 pt-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Información adicional</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

      {validationError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {validationError}
        </div>
      )}

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
          disabled={saving || !date || !dayOfWeek || !selectedProfileId || !selectedLevelId || !operationalStartStr || !operationalEndStr}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {saving ? 'Guardando...' : isEditing ? 'Actualizar' : 'Crear día'}
        </button>
      </div>
    </form>
  );
}