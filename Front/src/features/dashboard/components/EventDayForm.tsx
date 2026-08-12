import { useState, useEffect, useMemo } from 'react';
import { EventDayPhaseEditor, validatePhases } from './EventDayPhaseEditor';
import { useAttendanceLevels } from '../hooks/useAttendanceLevels';
import { useOperationalPhaseCatalog } from '../hooks/useOperationalPhaseCatalog';
import type { NormalizedPhase } from '../utils/operationalMinutes';
import { minutesToTimeStr, timeStrToMinutes, resolveOperationalMinutes, resolveOperationalWindow } from '../utils/operationalMinutes';
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

const TIMELINE_COLORS = ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500', 'bg-teal-500'];

function PhaseTimelineBar({
  phases, operationalStartMin, operationalEndMin, operationalPhases,
}: {
  phases: NormalizedPhase[];
  operationalStartMin: number;
  operationalEndMin: number;
  operationalPhases: { id: string; name: string; sort_order: number }[];
}) {
  const opWindow = resolveOperationalWindow(operationalStartMin, operationalEndMin);
  const range = opWindow.end - opWindow.start;
  if (range <= 0) return null;

  const sortedPhases = [...phases].sort((a, b) => {
    const aOp = operationalPhases.find((p) => p.id === a.operational_phase_id);
    const bOp = operationalPhases.find((p) => p.id === b.operational_phase_id);
    return (aOp?.sort_order ?? 0) - (bOp?.sort_order ?? 0);
  });

  const visiblePhases = sortedPhases.filter((p) => p.start_min !== null && p.end_min !== null);

  return (
    <div className="relative h-8 bg-slate-100 rounded-full overflow-hidden">
      {visiblePhases.map((phase, index) => {
        if (phase.start_min === null || phase.end_min === null) return null;

        const startMin = phase.start_min;
        const endMin = phase.end_min;
        const left = ((startMin - opWindow.start) / range) * 100;
        const width = ((endMin - startMin) / range) * 100;
        const op = operationalPhases.find((p) => p.id === phase.operational_phase_id);
        return (
          <div
            key={phase.operational_phase_id}
            className={`absolute top-0 h-full ${TIMELINE_COLORS[index % TIMELINE_COLORS.length]} opacity-60`}
            style={{ left: `${Math.max(0, left)}%`, width: `${Math.max(0, width)}%` }}
            title={op ? `${op.name}: ${minutesToTimeStr(startMin)}-${minutesToTimeStr(endMin)}` : ''}
          />
        );
      })}
    </div>
  );
}

export function EventDayForm({ eventDay, onSave, onCancel, saving }: EventDayFormProps) {
  const isEditing = !!eventDay;

  const [date, setDate] = useState('');
  const [dayOfWeek, setDayOfWeek] = useState('');
  const [weather, setWeather] = useState('');
  const [headlinerArtist, setHeadlinerArtist] = useState('');
  const [notes, setNotes] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [estimatedVehicles, setEstimatedVehicles] = useState('');
  const [averageParkingDuration, setAverageParkingDuration] = useState('');

  const { levels, loading: levelsLoading } = useAttendanceLevels(eventDay?.event_id ?? '', eventDay?.id ?? '');
  const { byId: operationalPhaseCatalog, loading: operationalPhasesLoading } = useOperationalPhaseCatalog();

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
      setOperationalStartStr(minutesToTimeStr(eventDay.operational_start_min));
      setOperationalEndStr(minutesToTimeStr(eventDay.operational_end_min));
      setNotes(eventDay.notes ?? '');
      setIsActive(eventDay.is_active);
      setEstimatedVehicles(eventDay.estimated_vehicles != null ? String(eventDay.estimated_vehicles) : '');
      setAverageParkingDuration(eventDay.average_parking_duration != null ? String(eventDay.average_parking_duration) : '');
      if (eventDay.phases && eventDay.phases.length > 0) {
        setEventDayPhases(
          eventDay.phases.map((p) => ({
            operational_phase_id: p.operational_phase_id,
            start_min: p.start_min,
            end_min: p.end_min,
            intensity: p.intensity ?? 1,
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

  const operationalPhases = useMemo(
    () => Object.values(operationalPhaseCatalog).sort((a, b) => a.sort_order - b.sort_order),
    [operationalPhaseCatalog],
  );

  const resolvedPhases = useMemo(
    () => resolveOperationalMinutes(eventDayPhases, operationalStartMin, operationalEndMin, operationalPhases),
    [eventDayPhases, operationalStartMin, operationalEndMin, operationalPhases],
  );

  const resolvedOpEnd = useMemo(
    () => resolveOperationalWindow(operationalStartMin, operationalEndMin).end,
    [operationalStartMin, operationalEndMin],
  );

  const currentPhaseErrors = useMemo(
    () => validatePhases(resolvedPhases, operationalStartMin, resolvedOpEnd),
    [resolvedPhases, operationalStartMin, resolvedOpEnd],
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!date || !dayOfWeek) {
      setValidationError('Completá todos los campos obligatorios');
      return;
    }
    if (!operationalStartStr || !operationalEndStr) {
      setValidationError('La ventana operativa es obligatoria');
      return;
    }
    if (currentPhaseErrors.length > 0) {
      setValidationError('Corregí los errores en las fases antes de guardar');
      return;
    }

    const payload: EventDayCreatePayload = {
      date,
      day_of_week: dayOfWeek,
      operational_start_min: operationalStartMin,
      operational_end_min: resolvedOpEnd,
      phases: resolvedPhases.map((p) => ({
        operational_phase_id: p.operational_phase_id,
        start_min: p.start_min,
        end_min: p.end_min,
        intensity: p.intensity,
      })),
      weather: weather || null,
      headliner_artist: headlinerArtist || null,
      notes: notes || null,
      estimated_vehicles: estimatedVehicles === '' ? null : Number(estimatedVehicles),
      average_parking_duration: averageParkingDuration === '' ? null : Number(averageParkingDuration),
      is_active: isActive,
    };

    await onSave(payload);
  };

  const hasPhases = eventDayPhases.length > 0;
  const hasAnyFilledPhase = resolvedPhases.some((p) => p.start_min !== null && p.end_min !== null);

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
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
            <div className="font-medium text-slate-700 mb-1">Niveles de asistencia del día</div>
            {levelsLoading ? (
              <span>Cargando niveles...</span>
            ) : levels.length === 0 ? (
              <span>No hay niveles cargados para este día. Use la gestión de niveles de asistencia.</span>
            ) : (
              <ul className="list-disc pl-5 space-y-1">
                {levels.map((l) => (
                  <li key={l.id}>
                    {l.name}: {l.min_people.toLocaleString()}–{l.max_people ? l.max_people.toLocaleString() : '∞'}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Estimación de vehículos</label>
          <input
            type="number"
            min={0}
            value={estimatedVehicles}
            onChange={(e) => setEstimatedVehicles(e.target.value)}
            placeholder="Ej: 5000"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-[10px] text-slate-400 mt-0.5">
            Vehículos estimados que se espera que ingresen al territorio durante este día. Independiente del nivel de asistencia.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Permanencia promedio del vehículo</label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={0}
              step="0.25"
              value={averageParkingDuration}
              onChange={(e) => setAverageParkingDuration(e.target.value)}
              placeholder="Ej: 4"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-sm text-slate-500 whitespace-nowrap">horas</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-0.5">
            Tiempo promedio que un vehículo permanece estacionado durante este día. Hipótesis inicial: 4 horas.
          </p>
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
        </div>
      </div>

      {operationalPhasesLoading ? (
        <div className="text-xs text-slate-400">Cargando fases operativas...</div>
      ) : (
        <div className="border-t border-slate-200 pt-4">
<EventDayPhaseEditor
                phases={eventDayPhases}
                operationalPhases={operationalPhases}
                onChange={setEventDayPhases}
                errors={currentPhaseErrors}
              />
              {hasPhases && hasAnyFilledPhase && (
                <div className="mt-3">
                  <PhaseTimelineBar
                    phases={resolvedPhases}
                    operationalStartMin={operationalStartMin}
                    operationalEndMin={operationalEndMin}
                    operationalPhases={operationalPhases}
                  />
                </div>
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
          disabled={saving || !date || !dayOfWeek || !operationalStartStr || !operationalEndStr}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {saving ? 'Guardando...' : isEditing ? 'Actualizar' : 'Crear día'}
        </button>
      </div>
    </form>
  );
}
