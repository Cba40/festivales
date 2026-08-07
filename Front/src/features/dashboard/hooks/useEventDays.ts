import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type { EventDaySummary } from '../types';

export function useEventDays(eventId: string) {
  const [eventDays, setEventDays] = useState<EventDaySummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchList = useCallback(async () => {
    if (!eventId) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<EventDaySummary[]>(
        endpoints.eventDays.list(eventId)
      );
      setEventDays(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar días del evento');
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  return {
    eventDays,
    loading,
    error,
    refresh: fetchList,
  };
}
