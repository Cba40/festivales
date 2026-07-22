import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type { OperationalEventDTO } from '../types';

export function useOperationalEvents(eventDayId: string | null) {
  const [events, setEvents] = useState<OperationalEventDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchList = useCallback(async () => {
    if (!eventDayId) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<OperationalEventDTO[]>(
        endpoints.operationalEvents.list(eventDayId)
      );
      setEvents(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar eventos operativos');
    } finally {
      setLoading(false);
    }
  }, [eventDayId]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  return { events, loading, error, refresh: fetchList };
}
