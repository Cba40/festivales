import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import type { OperationalPhaseDTO } from '../types';
import { useOperationalProfiles } from './useOperationalProfiles';

export type OperationalPhaseCatalog = Record<string, OperationalPhaseDTO>;

export function useOperationalPhaseCatalog() {
  const { profiles, loading: profilesLoading } = useOperationalProfiles();
  const [byId, setById] = useState<OperationalPhaseCatalog>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (profiles.length === 0) {
      setById({});
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const results = await Promise.all(
        profiles.map((profile) =>
          apiClient.get<OperationalPhaseDTO[]>(`/operational-phases/by-profile/${profile.id}`)
        )
      );
      const catalog: OperationalPhaseCatalog = {};
      for (const res of results) {
        for (const phase of res.data) {
          catalog[phase.id] = phase;
        }
      }
      setById(catalog);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar las fases operativas');
    } finally {
      setLoading(false);
    }
  }, [profiles]);

  useEffect(() => { fetch(); }, [fetch]);

  return { byId, loading, error, refresh: fetch, profilesLoading };
}