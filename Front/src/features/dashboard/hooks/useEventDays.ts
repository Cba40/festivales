import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type { EventDaySummary, EventDay } from '../types';

export function useEventDays(eventId: string) {
  const [eventDays, setEventDays] = useState<EventDaySummary[]>([]);
  const [todayEventDay, setTodayEventDay] = useState<EventDay | null>(null);
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

  const fetchToday = useCallback(async () => {
    if (!eventId) return null;
    try {
      const { data } = await apiClient.get<EventDay | null>(
        endpoints.eventDays.today(eventId)
      );
      setTodayEventDay(data);
      return data;
    } catch {
      return null;
    }
  }, [eventId]);

  useEffect(() => {
    fetchList();
    fetchToday();
  }, [fetchList, fetchToday]);

  return {
    eventDays,
    todayEventDay,
    loading,
    error,
    refresh: fetchList,
    refreshToday: fetchToday,
  };
}
