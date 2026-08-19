import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type { ServiceConfigDTO, ServiceConfigFilters } from '../types';

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