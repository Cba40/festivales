import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type { ServiceConfigDTO, ServiceConfigFilters } from '../types';

/**
 * Busca la config DEFAULT (event_day_id NULL) de un subtipo.
 * GET /service-configs sin event_day_id devuelve solo defaults (backend).
 * Devuelve null si no existe.
 */
export async function fetchDefaultServiceConfig(
  zoneTypeId: string,
  subtipo: string
): Promise<ServiceConfigDTO | null> {
  const { data: rows } = await apiClient.get<ServiceConfigDTO[]>(
    endpoints.serviceConfigs.list(),
    { params: { zone_type_id: zoneTypeId, subtipo } }
  );
  return rows.find((r) => r.event_day_id === null) ?? null;
}

export function useServiceConfigs(filters: ServiceConfigFilters = {}) {
  const [data, setData] = useState<ServiceConfigDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (filters.zone_type_id) params.zone_type_id = filters.zone_type_id;
      if (filters.subtipo) params.subtipo = filters.subtipo;
      if (filters.event_day_id) params.event_day_id = filters.event_day_id;

      const { data: rows } = await apiClient.get<ServiceConfigDTO[]>(
        endpoints.serviceConfigs.list(),
        { params }
      );
      setData(rows);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar configuraciones de servicios');
    } finally {
      setLoading(false);
    }
  }, [filters.zone_type_id, filters.subtipo, filters.event_day_id]);

  useEffect(() => { void fetch(); }, [fetch]);

  return { data, loading, error, refresh: fetch };
}