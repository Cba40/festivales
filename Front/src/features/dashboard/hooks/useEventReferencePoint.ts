import { useState, useCallback } from 'react';
import { apiClient } from '../../../core/api/client';
import { endpoints } from '../../../core/api/endpoints';
import type { EventDTO, EventReferencePointPayload } from '../types';

const DEFAULT_EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function useEventReferencePoint(eventId: string = DEFAULT_EVENT_ID) {
  const [event, setEvent] = useState<EventDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<EventDTO>(endpoints.events.get(eventId));
      setEvent(res.data);
    } catch (err) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Error al cargar el evento';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  const save = useCallback(
    async (payload: EventReferencePointPayload) => {
      setSaving(true);
      setError(null);
      setSaved(false);
      try {
        const res = await apiClient.put<EventDTO>(
          endpoints.events.update(eventId),
          payload
        );
        setEvent(res.data);
        setSaved(true);
        return true;
      } catch (err) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Error al guardar el punto de referencia operacional';
        setError(msg);
        return false;
      } finally {
        setSaving(false);
      }
    },
    [eventId]
  );

  return { event, loading, saving, saved, error, load, save };
}