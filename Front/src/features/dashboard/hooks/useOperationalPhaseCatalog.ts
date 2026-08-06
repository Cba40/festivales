import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import type { OperationalPhaseDTO } from '../types';

export type OperationalPhaseCatalog = Record<string, OperationalPhaseDTO>;

export function useOperationalPhaseCatalog() {
  const [byId, setById] = useState<OperationalPhaseCatalog>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<OperationalPhaseDTO[]>(
        '/operational-phases/'
      );
      const catalog: OperationalPhaseCatalog = {};
      for (const phase of data) {
        catalog[phase.id] = phase;
      }
      setById(catalog);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar las fases operativas');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  return { byId, loading, error, refresh: fetch };
}