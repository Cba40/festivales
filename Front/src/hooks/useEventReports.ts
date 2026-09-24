import { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../core/api/client';

export interface UseEventReportOptions {
  params?: Record<string, unknown>;
  enabled?: boolean;
}

function extractErrorMessage(err: unknown): string {
  const error = err as { response?: { status?: number; data?: { detail?: string } } };
  if (error?.response?.status === 404) {
    return 'Endpoint de informe no disponible.';
  }
  if (error?.response?.status === undefined) {
    return 'No se pudo conectar con el servicio de informes.';
  }
  return error?.response?.data?.detail ?? 'Error al cargar el informe.';
}

export function useEventReport<T>(
  eventId: string,
  url: string,
  options: UseEventReportOptions = {}
) {
  const { params, enabled = true } = options;
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!eventId) return;
    setIsLoading(true);
    setError(null);
    try {
      const { data: response } = await apiClient.get<T>(url, { params });
      setData(response);
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [eventId, url, params]);

  useEffect(() => {
    if (enabled) void refresh();
  }, [refresh, enabled]);

  return { data, isLoading, error, refresh };
}