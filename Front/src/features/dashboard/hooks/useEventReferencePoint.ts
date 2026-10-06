import { useState, useCallback } from 'react';
import { apiClient } from '../../../core/api/client';
import { endpoints } from '../../../core/api/endpoints';
import type { EventDTO, EventReferencePointPayload } from '../types';
import { useAppStore } from '../../../core/state/store';

/**
 * Punto de referencia del evento activo.
 *
 * `eventId` es opcional: sin argumento usa el del store global (`activeEventId`,
 * resuelto por `useActiveEvent()`). Antes el default venía de
 * `import.meta.env.VITE_EVENT_ID`, horneado en el bundle al compilar.
 */
export function useEventReferencePoint(eventId?: string) {
  const activeEventId = useAppStore((state) => state.activeEventId);
  const resolvedEventId = eventId ?? activeEventId;
  const [event, setEvent] = useState<EventDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    // Todavia no resolvio el evento activo: no hay contra que consultar.
    if (!resolvedEventId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<EventDTO>(endpoints.events.get(resolvedEventId));
      setEvent(res.data);
    } catch (err) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Error al cargar el evento';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [resolvedEventId]);

  const save = useCallback(
    async (payload: EventReferencePointPayload) => {
      if (!resolvedEventId) {
        setError('No hay evento activo configurado. Marcá una jornada como activa desde el dashboard.');
        return false;
      }
      setSaving(true);
      setError(null);
      setSaved(false);
      try {
        const res = await apiClient.put<EventDTO>(
          endpoints.events.update(resolvedEventId),
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
    [resolvedEventId]
  );

  return { event, loading, saving, saved, error, load, save };
}