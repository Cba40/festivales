import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type { PublicAlertsResponse } from '@/features/dashboard/types';

export function usePublicAlerts(eventId: string, intervalMs = 30000) {
  const [data, setData] = useState<PublicAlertsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await apiClient.get<PublicAlertsResponse>(
        endpoints.products.alerts(eventId)
      );
      setData(res.data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar avisos');
    }
  }, [eventId]);

  useEffect(() => {
    load();
    const id = setInterval(load, intervalMs);
    return () => clearInterval(id);
  }, [load, intervalMs]);

  return { data, error, refresh: load };
}