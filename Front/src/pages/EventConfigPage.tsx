import { useEffect, useCallback } from 'react';
import { useState } from 'react';
import { EVENT_ID } from '../components/context-engine/constants';
import { PredictionsDashboard } from '../components/context-engine/PredictionsDashboard';
import { apiClient } from '../core/api/client';

interface EventDaySummary {
  id: string;
  date: string;
  is_active: boolean;
}

export function EventConfigPage() {
  const [eventDays, setEventDays] = useState<EventDaySummary[]>([]);
  const [selectedDayId, setSelectedDayId] = useState<string | null>(null);
  const [loadingDays, setLoadingDays] = useState(true);

  const loadDays = useCallback(async () => {
    setLoadingDays(true);
    try {
      const { data } = await apiClient.get<EventDaySummary[]>(`/events/${EVENT_ID}/event-days`);
      setEventDays(data);
      const today = data.find(d => d.is_active);
      if (today) {
        setSelectedDayId(today.id);
      } else if (data.length > 0) {
        setSelectedDayId(data[0].id);
      }
    } catch {
      /* ignore */
    } finally {
      setLoadingDays(false);
    }
  }, []);

  useEffect(() => {
    loadDays();
  }, [loadDays]);

  return (
    <div className="max-w-7xl mx-auto space-y-4">
      <div className="flex justify-end">
        <select
          value={selectedDayId ?? ''}
          onChange={(e) => setSelectedDayId(e.target.value || null)}
          className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          disabled={loadingDays}
        >
          {loadingDays && <option value="">Cargando...</option>}
          {!loadingDays && eventDays.length === 0 && (
            <option value="">Sin jornadas</option>
          )}
          {eventDays.map(d => (
            <option key={d.id} value={d.id}>
              {d.date} {d.is_active ? '(Hoy)' : ''}
            </option>
          ))}
        </select>
      </div>

      {!selectedDayId && !loadingDays && (
        <div className="text-center py-12 text-slate-400 italic">
          No hay jornadas disponibles.
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <PredictionsDashboard eventId={EVENT_ID} />
      </div>
    </div>
  );
}