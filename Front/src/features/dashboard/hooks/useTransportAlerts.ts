import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type {
  TransportAlertDTO,
  TransportAlertCreatePayload,
  TransportAlertUpdatePayload,
} from '../types';

const BACKEND_ERROR_MAP: Array<[RegExp, string]> = [
  [/TransportAlert not found/i, 'La alerta no existe'],
  [/valid_until must be greater than valid_from/i, 'La fecha de fin debe ser posterior al inicio'],
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

export function useTransportAlerts(eventId: string | null) {
  const [alerts, setAlerts] = useState<TransportAlertDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!eventId) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<TransportAlertDTO[]>(
        endpoints.adminAlerts.list(eventId)
      );
      setAlerts(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar alertas');
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const create = useCallback(
    async (payload: TransportAlertCreatePayload): Promise<TransportAlertDTO | null> => {
      if (!eventId) return null;
      setSaving(true);
      setActionError(null);
      try {
        const { data } = await apiClient.post<TransportAlertDTO>(
          endpoints.adminAlerts.create(eventId),
          payload
        );
        await refresh();
        return data;
      } catch (err: unknown) {
        setActionError(backendErrorToSpanish(err, 'Error al crear alerta'));
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
      payload: TransportAlertUpdatePayload
    ): Promise<TransportAlertDTO | null> => {
      if (!eventId) return null;
      setSaving(true);
      setActionError(null);
      try {
        const { data } = await apiClient.put<TransportAlertDTO>(
          endpoints.adminAlerts.update(eventId, id),
          payload
        );
        await refresh();
        return data;
      } catch (err: unknown) {
        setActionError(backendErrorToSpanish(err, 'Error al actualizar alerta'));
        return null;
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
        await apiClient.delete(endpoints.adminAlerts.delete(eventId, id));
        await refresh();
        return true;
      } catch (err: unknown) {
        setActionError(backendErrorToSpanish(err, 'Error al eliminar alerta'));
        return false;
      } finally {
        setSaving(false);
      }
    },
    [eventId, refresh]
  );

  const deactivate = useCallback(
    async (id: string): Promise<boolean> => {
      if (!eventId) return false;
      setSaving(true);
      setActionError(null);
      try {
        await apiClient.patch(endpoints.adminAlerts.deactivate(eventId, id));
        await refresh();
        return true;
      } catch (err: unknown) {
        setActionError(backendErrorToSpanish(err, 'Error al desactivar alerta'));
        return false;
      } finally {
        setSaving(false);
      }
    },
    [eventId, refresh]
  );

  return { alerts, loading, error, refresh, create, update, remove, deactivate, saving, actionError };
}