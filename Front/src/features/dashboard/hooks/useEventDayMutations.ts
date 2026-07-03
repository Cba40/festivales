import { useState, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type { EventDay, EventDayCreatePayload } from '../types';

export function useEventDayMutations(eventId: string) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(
    async (payload: EventDayCreatePayload): Promise<EventDay | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.post<EventDay>(
          endpoints.eventDays.list(eventId),
          payload
        );
        return data;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al crear día del evento';
        setError(msg);
        return null;
      } finally {
        setSaving(false);
      }
    },
    [eventId]
  );

  const update = useCallback(
    async (dayId: string, payload: Partial<EventDayCreatePayload>): Promise<EventDay | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.put<EventDay>(
          endpoints.eventDays.byId(eventId, dayId),
          payload
        );
        return data;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al actualizar día del evento';
        setError(msg);
        return null;
      } finally {
        setSaving(false);
      }
    },
    [eventId]
  );

  const remove = useCallback(
    async (dayId: string): Promise<boolean> => {
      setSaving(true);
      setError(null);
      try {
        await apiClient.delete(endpoints.eventDays.byId(eventId, dayId));
        return true;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al eliminar día del evento';
        setError(msg);
        return false;
      } finally {
        setSaving(false);
      }
    },
    [eventId]
  );

  return { create, update, remove, saving, error };
}
