import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type {
  OperatorMessageDTO,
  OperatorMessageCreatePayload,
  OperatorMessageUpdatePayload,
} from '../types';

const BACKEND_ERROR_MAP: Array<[RegExp, string]> = [
  [/OperatorMessage not found/i, 'El mensaje no existe'],
  [/expires_at must be greater than publish_at/i, 'La fecha de expiración debe ser posterior a la de publicación'],
  [/event_id in body must match URL path/i, 'El evento del cuerpo no coincide con la ruta'],
  [/Event with id '.*' not found/i, 'El evento indicado no existe'],
  [/TransportLine with id '.*' not found/i, 'La línea de transporte indicada no existe'],
];

function backendErrorToSpanish(err: unknown, fallback: string): string {
  const maybe =
    (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  let detail = '';
  if (typeof maybe === 'string') {
    detail = maybe;
  } else if (Array.isArray(maybe)) {
    const first = maybe[0] as { msg?: string; loc?: unknown[] } | undefined;
    const locParts = first?.loc;
    const loc = locParts && locParts.length > 0 ? String(locParts[locParts.length - 1]) : '';
    detail = first?.msg ?? '';
    if (detail && loc) detail = `${loc}: ${detail}`;
  } else if (maybe === null || maybe === undefined) {
    detail = err instanceof Error ? err.message : '';
  }
  for (const [pattern, message] of BACKEND_ERROR_MAP) {
    if (pattern.test(detail)) return message;
  }
  return detail || fallback;
}

export function useOperatorMessages(eventId: string | null) {
  const [messages, setMessages] = useState<OperatorMessageDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!eventId) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<OperatorMessageDTO[]>(
        endpoints.operatorMessages.list(eventId)
      );
      setMessages(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar mensajes');
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const create = useCallback(
    async (payload: OperatorMessageCreatePayload): Promise<OperatorMessageDTO | null> => {
      if (!eventId) return null;
      setSaving(true);
      setActionError(null);
      try {
        const { data } = await apiClient.post<OperatorMessageDTO>(
          endpoints.operatorMessages.create(eventId),
          payload
        );
        await refresh();
        return data;
      } catch (err: unknown) {
        setActionError(backendErrorToSpanish(err, 'Error al crear mensaje'));
        return null;
      } finally {
        setSaving(false);
      }
    },
    [eventId, refresh]
  );

  const update = useCallback(
    async (
      id: string,
      payload: OperatorMessageUpdatePayload
    ): Promise<OperatorMessageDTO | null> => {
      if (!eventId) return null;
      setSaving(true);
      setActionError(null);
      try {
        const { data } = await apiClient.put<OperatorMessageDTO>(
          endpoints.operatorMessages.update(eventId, id),
          payload
        );
        await refresh();
        return data;
      } catch (err: unknown) {
        setActionError(backendErrorToSpanish(err, 'Error al actualizar mensaje'));
        return null;
      } finally {
        setSaving(false);
      }
    },
    [eventId, refresh]
  );

  const publish = useCallback(
    async (id: string): Promise<boolean> => {
      if (!eventId) return false;
      setSaving(true);
      setActionError(null);
      try {
        await apiClient.patch(endpoints.operatorMessages.publish(eventId, id));
        await refresh();
        return true;
      } catch (err: unknown) {
        setActionError(backendErrorToSpanish(err, 'Error al publicar mensaje'));
        return false;
      } finally {
        setSaving(false);
      }
    },
    [eventId, refresh]
  );

  const cancel = useCallback(
    async (id: string): Promise<boolean> => {
      if (!eventId) return false;
      setSaving(true);
      setActionError(null);
      try {
        await apiClient.patch(endpoints.operatorMessages.cancel(eventId, id));
        await refresh();
        return true;
      } catch (err: unknown) {
        setActionError(backendErrorToSpanish(err, 'Error al cancelar mensaje'));
        return false;
      } finally {
        setSaving(false);
      }
    },
    [eventId, refresh]
  );

  const remove = useCallback(
    async (id: string): Promise<boolean> => {
      if (!eventId) return false;
      setSaving(true);
      setActionError(null);
      try {
        await apiClient.delete(endpoints.operatorMessages.delete(eventId, id));
        await refresh();
        return true;
      } catch (err: unknown) {
        setActionError(backendErrorToSpanish(err, 'Error al eliminar mensaje'));
        return false;
      } finally {
        setSaving(false);
      }
    },
    [eventId, refresh]
  );

  return { messages, loading, error, refresh, create, update, publish, cancel, remove, saving, actionError };
}