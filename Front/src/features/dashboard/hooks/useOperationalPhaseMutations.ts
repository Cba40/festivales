import { useState, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import type { OperationalPhaseDTO } from '../types';

export interface PhaseCreatePayload {
  operational_profile_id: string;
  name: string;
  start_min: number;
  end_min: number;
  sort_order: number;
}

export interface PhaseUpdatePayload {
  name?: string;
  start_min?: number;
  end_min?: number;
  sort_order?: number;
}

export function useOperationalPhaseMutations() {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(
    async (payload: PhaseCreatePayload): Promise<OperationalPhaseDTO | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.post<OperationalPhaseDTO>(
          '/operational-phases/',
          payload
        );
        return data;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al crear fase operativa';
        setError(msg);
        return null;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const update = useCallback(
    async (id: string, payload: PhaseUpdatePayload): Promise<OperationalPhaseDTO | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.put<OperationalPhaseDTO>(
          `/operational-phases/${id}`,
          payload
        );
        return data;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al actualizar fase operativa';
        setError(msg);
        return null;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const remove = useCallback(
    async (id: string): Promise<boolean> => {
      setSaving(true);
      setError(null);
      try {
        await apiClient.delete(`/operational-phases/${id}`);
        return true;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al eliminar fase operativa';
        setError(msg);
        return false;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  return { create, update, remove, saving, error };
}
