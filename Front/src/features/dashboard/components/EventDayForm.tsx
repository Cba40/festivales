import { useState, useEffect } from 'react';
import { apiClient } from '@/core/api/client';
import type { EventDay, EventDayCreatePayload, OperationalProfileDTO, OperationalPhaseDTO } from '../types';

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
  const [estimatedAttendance, setEstimatedAttendance] = useState('');
  const [notes, setNotes] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [validationError, setValidationError] = useState<string | null>(null);

  const [profiles, setProfiles] = useState<OperationalProfileDTO[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [phases, setPhases] = useState<OperationalPhaseDTO[]>([]);
  const [phasesLoading, setPhasesLoading] = useState(false);
  const [profilesLoading, setProfilesLoading] = useState(false);

  const [operationalStartStr, setOperationalStartStr] = useState('');
  const [operationalEndStr, setOperationalEndStr] = useState('');

  useEffect(() => {
    setProfilesLoading(true);
    apiClient.get<OperationalProfileDTO[]>('/operational-profiles/')
      .then(({ data }) => setProfiles(data))
      .catch(() => {})
      .finally(() => setProfilesLoading(false));
  }, []);

  useEffect(() => {
    if (eventDay) {
      setDate(eventDay.date);
      setDayOfWeek(eventDay.day_of_week);
      setWeather(eventDay.weather ?? '');
      setHeadlinerArtist(eventDay.headliner_artist ?? '');
      setEstimatedAttendance(eventDay.estimated_attendance?.toString() ?? '');
      setSelectedProfileId(eventDay.operational_profile_id);
      setOperationalStartStr(minutesToTimeStr(eventDay.operational_start_min));
      setOperationalEndStr(minutesToTimeStr(eventDay.operational_end_min));
      setNotes(eventDay.notes ?? '');
      setIsActive(eventDay.is_active);
    }
  }, [eventDay]);

  useEffect(() => {
    if (!selectedProfileId) {
      setPhases([]);
      return;
    }
    setPhasesLoading(true);
    apiClient.get<OperationalPhaseDTO[]>(`/operational-phases/by-profile/${selectedProfileId}`)
      .then(({ data }) => setPhases(data))
      .catch(() => setPhases([]))
      .finally(() => setPhasesLoading(false));
  }, [selectedProfileId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);
    if (!date || !dayOfWeek || !selectedProfileId) return;

    if (!operationalStartStr || !operationalEndStr) {
      setValidationError('La ventana operativa es obligatoria');
      return;
    }

    const startMin = timeStrToMinutes(operationalStartStr);
    const endMin = timeStrToMinutes(operationalEndStr);

    if (endMin <= startMin) {
      setValidationError('El fin de jornada territorial debe ser posterior al inicio');
      return;
    }

    const payload: EventDayCreatePayload = {
      date,
      day_of_week: dayOfWeek,
      operational_profile_id: selectedProfileId,
      operational_start_min: startMin,
      operational_end_min: endMin,
      weather: weather || null,
      headliner_artist: headlinerArtist || null,
      estimated_attendance: estimatedAttendance ? parseInt(estimatedAttendance, 10) : 0,
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

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-slate-700 mb-1">Perfil operativo *</label>
          <select
            value={selectedProfileId}
            onChange={(e) => setSelectedProfileId(e.target.value)}
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
            value={estimatedAttendance}
            onChange={(e) => setEstimatedAttendance(e.target.value)}
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

      {selectedProfileId && (
        <div className="border-t border-slate-200 pt-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-2">Fases del perfil operativo</h3>
          <p className="text-xs text-slate-500 mb-3">
            Las fases se gestionan en la configuración de perfiles operativos. Esta vista es informativa.
          </p>
          {phasesLoading ? (
            <div className="text-xs text-slate-400">Cargando fases...</div>
          ) : phases.length === 0 ? (
            <div className="text-xs text-slate-400">Sin fases definidas para este perfil.</div>
          ) : (
            <div className="space-y-2">
              {phases
                .slice().sort((a, b) => a.sort_order - b.sort_order)
                .map((phase) => (
                  <div
                    key={phase.id}
                    className="flex items-center gap-3 p-2 bg-slate-50 rounded-lg border border-slate-100"
                  >
                    <span className="text-xs font-semibold text-slate-600 w-16 text-center">
                      {minutesToTimeStr(phase.start_min)}
                    </span>
                    <div className="flex-1 h-1.5 bg-blue-100 rounded-full">
                      <div
                        className="h-1.5 bg-blue-500 rounded-full"
                        style={{
                          width: `${Math.min(100, ((phase.end_min - phase.start_min) / 120) * 100)}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs font-semibold text-slate-600 w-16 text-center">
                      {minutesToTimeStr(phase.end_min)}
                    </span>
                    <span className="text-sm font-medium text-slate-700 min-w-[120px]">{phase.name}</span>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

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
          disabled={saving || !date || !dayOfWeek || !selectedProfileId || !operationalStartStr || !operationalEndStr}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {saving ? 'Guardando...' : isEditing ? 'Actualizar' : 'Crear día'}
        </button>
      </div>
    </form>
  );
}
