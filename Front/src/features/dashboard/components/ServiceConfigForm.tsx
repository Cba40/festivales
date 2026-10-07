import { useState, useEffect } from 'react';
import type { EventDaySummary, ServiceConfigDTO, ZoneTypeDTO } from '../types';

interface ServiceConfigFormProps {
  initial?: ServiceConfigDTO | null;
  zoneTypes: ZoneTypeDTO[];
  eventDays: EventDaySummary[];
  onSave: (payload: {
    zone_type_id: string;
    subtipo?: string | null;
    event_day_id?: string | null;
    average_duration_min: number;
    bathroom_use_rate_per_person_hour?: number | null;
  }) => Promise<void>;
  onCancel: () => void;
  saving: boolean;
}

export function ServiceConfigForm({
  initial,
  zoneTypes,
  eventDays,
  onSave,
  onCancel,
  saving,
}: ServiceConfigFormProps) {
  const [zoneTypeId, setZoneTypeId] = useState('');
  const [subtipo, setSubtipo] = useState('');
  const [eventDayId, setEventDayId] = useState('');
  const [duration, setDuration] = useState('');
  const [bathroomUseRate, setBathroomUseRate] = useState('0.1');
  const [validationError, setValidationError] = useState<string | null>(null);
  const isBathroom = subtipo.trim().toLowerCase() === 'banos';

  useEffect(() => {
    if (initial) {
      setZoneTypeId(initial.zone_type_id);
      setSubtipo(initial.subtipo ?? '');
      setEventDayId(initial.event_day_id ?? '');
      setDuration(initial.average_duration_min.toString());
      setBathroomUseRate(
        initial.bathroom_use_rate_per_person_hour?.toString() ?? '0.1'
      );
    } else {
      setZoneTypeId('');
      setSubtipo('');
      setEventDayId('');
      setDuration('');
      setBathroomUseRate('0.1');
    }
  }, [initial]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!zoneTypeId) {
      setValidationError('El tipo de zona es obligatorio');
      return;
    }

    const parsedDuration = parseInt(duration, 10);
    if (isNaN(parsedDuration) || parsedDuration <= 0) {
      setValidationError('La permanencia debe ser un número entero mayor a 0 (en minutos)');
      return;
    }

    const payload = {
      zone_type_id: zoneTypeId,
      subtipo: subtipo.trim() || null,
      event_day_id: eventDayId || null,
      average_duration_min: parsedDuration,
    };
    if (isBathroom) {
      const parsedUseRate = Number(bathroomUseRate);
      if (!Number.isFinite(parsedUseRate) || parsedUseRate < 0) {
        setValidationError(
          'La tasa de uso debe ser un número mayor o igual a 0'
        );
        return;
      }
      if (!/^\d+(\.\d{1,2})?$/.test(bathroomUseRate.trim())) {
        setValidationError(
          'La tasa de uso admite máximo 2 decimales (ej: 0.1, 0.25)'
        );
        return;
      }
      await onSave({
        ...payload,
        bathroom_use_rate_per_person_hour: parsedUseRate,
      });
      return;
    }
    await onSave(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Tipo de zona *</label>
        <select
          value={zoneTypeId}
          onChange={(e) => setZoneTypeId(e.target.value)}
          required
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Seleccioná un tipo de zona</option>
          {zoneTypes.map((zt) => (
            <option key={zt.id} value={zt.id}>
              {zt.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Subtipo (opcional)</label>
        <input
          type="text"
          value={subtipo}
          onChange={(e) => setSubtipo(e.target.value)}
          placeholder='Ej: "banos", "hidratacion"'
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Jornada (opcional — vacío = Default global)
        </label>
        <select
          value={eventDayId}
          onChange={(e) => setEventDayId(e.target.value)}
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Default global (todas las jornadas)</option>
          {eventDays.map((day) => (
            <option key={day.id} value={day.id}>
              {day.date}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Permanencia (minutos) *</label>
        <input
          type="number"
          min={1}
          value={duration}
          onChange={(e) => setDuration(e.target.value)}
          required
          placeholder="Ej: 15"
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <p className="text-[10px] text-slate-400 mt-0.5">
        Permanencia media del servicio en minutos; Bathroom V1 la convierte a horas para la Ley de
        Little.
      </p>

      {isBathroom && (
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Tasa de uso (usos/persona-hora) *
          </label>
          <input
            type="number"
            min={0}
            step="0.01"
            value={bathroomUseRate}
            onChange={(e) => setBathroomUseRate(e.target.value)}
            required
            title="Hipótesis inicial: 0.1. Calibrar con observaciones reales"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-[10px] text-slate-400 mt-0.5">
            Hipótesis inicial: 0.1. Calibrar con observaciones reales; no es un valor empírico
            validado. Máximo 2 decimales.
          </p>
        </div>
      )}

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
          disabled={saving || !zoneTypeId || !duration}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {saving ? 'Guardando...' : initial ? 'Actualizar' : 'Crear configuración'}
        </button>
      </div>
    </form>
  );
}