import { useState, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import type { ZoneBehaviorDTO } from '../types';

export interface ZoneBehaviorUpdatePayload {
  density_factor?: number;
  flow_restriction?: 'OPEN' | 'REGULATED' | 'CLOSED';
}

export function useZoneBehaviorMutations() {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = useCallback(
    async (id: string, payload: ZoneBehaviorUpdatePayload): Promise<ZoneBehaviorDTO | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.put<ZoneBehaviorDTO>(
          `/zone-behaviors/${id}`,
          payload
        );
        return data;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al actualizar comportamiento territorial';
        setError(msg);
        return null;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  return { update, saving, error };
}
