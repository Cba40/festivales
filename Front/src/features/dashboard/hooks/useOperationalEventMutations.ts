import { useState, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type { OperationalEventDTO, OperationalEventCreatePayload, OperationalEventUpdatePayload } from '../types';

export function useOperationalEventMutations() {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(
    async (payload: OperationalEventCreatePayload): Promise<OperationalEventDTO | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.post<OperationalEventDTO>(
          endpoints.operationalEvents.create,
          payload
        );
        return data;
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          (err instanceof Error ? err.message : 'Error al crear evento');
        setError(msg);
        return null;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const update = useCallback(
    async (id: string, payload: OperationalEventUpdatePayload): Promise<OperationalEventDTO | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.put<OperationalEventDTO>(
          endpoints.operationalEvents.byId(id),
          payload
        );
        return data;
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          (err instanceof Error ? err.message : 'Error al actualizar evento');
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
        await apiClient.delete(endpoints.operationalEvents.byId(id));
        return true;
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          (err instanceof Error ? err.message : 'Error al eliminar evento');
        setError(msg);
        return false;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const finalize = useCallback(
    async (id: string): Promise<OperationalEventDTO | null> => {
      return update(id, { is_active: false });
    },
    [update]
  );

  return { create, update, remove, finalize, saving, error };
}
