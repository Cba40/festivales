import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '../../../core/api/endpoints';
import type { AttendanceLevelDTO } from '../types';

export function useAttendanceLevels(eventId: string) {
  const [levels, setLevels] = useState<AttendanceLevelDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!eventId) {
      setLevels([]);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<AttendanceLevelDTO[]>(
        endpoints.attendanceLevels.list(eventId)
      );
      setLevels(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar niveles de asistencia');
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void fetch(); }, [fetch]);

  return { levels, loading, error, refresh: fetch };
}
