import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import type { OperationalPhaseDTO } from '../types';

export function useOperationalPhases(profileId: string | null) {
  const [phases, setPhases] = useState<OperationalPhaseDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!profileId) {
      setPhases([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<OperationalPhaseDTO[]>(
        `/operational-phases/by-profile/${profileId}`
      );
      setPhases(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar fases operativas');
    } finally {
      setLoading(false);
    }
  }, [profileId]);

  useEffect(() => { fetch(); }, [fetch]);

  return { phases, loading, error, refresh: fetch };
}
