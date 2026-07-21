import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import type { AttendanceLevelDTO } from '../types';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function useAttendanceLevels() {
  const [levels, setLevels] = useState<AttendanceLevelDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<AttendanceLevelDTO[]>(
        `/events/${EVENT_ID}/attendance-levels`
      );
      setLevels(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar niveles de asistencia');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  return { levels, loading, error, refresh: fetch };
}
