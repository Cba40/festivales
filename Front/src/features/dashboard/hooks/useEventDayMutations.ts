import { useState, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type { EventDay, EventDayCreatePayload } from '../types';

/**
 * `eventId` acepta `null` porque el store todavía no resolvió. Los tres guards
 * (`create`/`update`/`remove`) son obligatorios: sin ellos no se puede pasar el
 * valor nullable al endpoint, que exige `string`. Antes no existían y una
 * pantalla abierta durante la resolución mandaba `event_id: ''` al backend.
 */
export function useEventDayMutations(eventId: string | null) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(
    async (payload: EventDayCreatePayload): Promise<EventDay | null> => {
      if (!eventId) {
        setError('Evento no disponible');
        return null;
      }

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
      if (!eventId) {
        setError('Evento no disponible');
        return null;
      }

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
      if (!eventId) {
        setError('Evento no disponible');
        return false;
      }

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
