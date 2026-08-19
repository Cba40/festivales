import { useState, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type { ServiceConfigDTO, ServiceConfigCreatePayload } from '../types';

export function useServiceConfigMutations(refresh?: () => void | Promise<void>) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(
    async (payload: ServiceConfigCreatePayload): Promise<ServiceConfigDTO | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.post<ServiceConfigDTO>(
          endpoints.serviceConfigs.create(),
          payload
        );
        if (refresh) await refresh();
        return data;
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          (err instanceof Error ? err.message : 'Error al crear configuración');
        setError(msg);
        return null;
      } finally {
        setSaving(false);
      }
    },
    [refresh]
  );

  const update = useCallback(
    async (id: string, payload: ServiceConfigCreatePayload): Promise<ServiceConfigDTO | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.put<ServiceConfigDTO>(
          endpoints.serviceConfigs.update(id),
          payload
        );
        if (refresh) await refresh();
        return data;
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          (err instanceof Error ? err.message : 'Error al actualizar configuración');
        setError(msg);
        return null;
      } finally {
        setSaving(false);
      }
    },
    [refresh]
  );

  const remove = useCallback(
    async (id: string): Promise<boolean> => {
      setSaving(true);
      setError(null);
      try {
        await apiClient.delete(endpoints.serviceConfigs.delete(id));
        if (refresh) await refresh();
        return true;
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          (err instanceof Error ? err.message : 'Error al eliminar configuración');
        setError(msg);
        return false;
      } finally {
        setSaving(false);
      }
    },
    [refresh]
  );

  return { create, update, remove, saving, error };
}