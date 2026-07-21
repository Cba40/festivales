import { useState, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import type { OperationalProfileDTO } from '../types';

export interface ProfileCreatePayload {
  name: string;
  description?: string | null;
}

export interface ProfileUpdatePayload {
  name?: string;
  description?: string | null;
}

export function useOperationalProfileMutations() {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(
    async (payload: ProfileCreatePayload): Promise<OperationalProfileDTO | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.post<OperationalProfileDTO>(
          '/operational-profiles/',
          payload
        );
        return data;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al crear perfil operativo';
        setError(msg);
        return null;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const update = useCallback(
    async (id: string, payload: ProfileUpdatePayload): Promise<OperationalProfileDTO | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.put<OperationalProfileDTO>(
          `/operational-profiles/${id}`,
          payload
        );
        return data;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al actualizar perfil operativo';
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
        await apiClient.delete(`/operational-profiles/${id}`);
        return true;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al eliminar perfil operativo';
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
