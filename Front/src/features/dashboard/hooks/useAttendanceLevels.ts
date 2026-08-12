import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import type { AttendanceLevelDTO } from '../types';

export function useAttendanceLevels(eventId: string, eventDayId?: string) {
  const [levels, setLevels] = useState<AttendanceLevelDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!eventId || !eventDayId) {
      setLevels([]);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<AttendanceLevelDTO[]>(
        `/events/${eventId}/days/${eventDayId}/attendance-levels`
      );
      setLevels(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar niveles de asistencia');
    } finally {
      setLoading(false);
    }
  }, [eventId, eventDayId]);

  useEffect(() => { void fetch(); }, [fetch]);

  return { levels, loading, error, refresh: fetch };
}
