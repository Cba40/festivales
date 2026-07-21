import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import type { OperationalProfileDTO } from '../types';

export function useOperationalProfiles() {
  const [profiles, setProfiles] = useState<OperationalProfileDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<OperationalProfileDTO[]>('/operational-profiles/');
      setProfiles(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar perfiles operativos');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  return { profiles, loading, error, refresh: fetch };
}
