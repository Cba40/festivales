import { useState, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type { OperationalEventDTO, OperationalEventCreatePayload, OperationalEventUpdatePayload } from '../types';

const BACKEND_ERROR_MAP: Array<[RegExp, string]> = [
  [/Cannot modify expired event/i, 'No se puede modificar un evento expirado'],
  [/Cannot deactivate expired event/i, 'No se puede finalizar un evento expirado'],
  [/Cannot delete expired event/i, 'No se puede eliminar un evento expirado'],
  [/Cannot delete event that has been used by the prediction engine/i, 'No se puede eliminar: el evento ya fue utilizado por el motor'],
  [/OperationalEvent not found/i, 'El evento no existe'],
  [/EventDay with id '.*' not found/i, 'La jornada indicada no existe'],
  [/Zone with id '.*' not found/i, 'La zona indicada no existe'],
  [/end_timestamp must be greater than start_timestamp/i, 'La fecha de fin debe ser posterior a la de inicio'],
  [/effect_value must be between 1 and 100/i, 'El porcentaje de reducción debe estar entre 1 y 100'],
  [/effect_value must be >= 1/i, 'La cantidad de personas adicionales debe ser al menos 1'],
  [/effect_value must be NULL for (cierre_total|incidente_sin_impacto)/i, 'Este tipo de efecto no admite un valor numérico'],
  [/effect_value is required for/i, 'Se requiere un valor numérico para este tipo de efecto'],
];

function backendErrorToSpanish(err: unknown, fallback: string): string {
  const maybe =
    (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  let detail = '';
  if (typeof maybe === 'string') {
    detail = maybe;
  } else if (Array.isArray(maybe)) {
    const first = maybe[0] as { msg?: string; loc?: unknown[] } | undefined;
    const locParts = first?.loc;
    const loc = locParts && locParts.length > 0 ? String(locParts[locParts.length - 1]) : '';
    detail = first?.msg ?? '';
    if (detail && loc) detail = `${loc}: ${detail}`;
  } else if (maybe === null || maybe === undefined) {
    detail = err instanceof Error ? err.message : '';
  }
  for (const [pattern, message] of BACKEND_ERROR_MAP) {
    if (pattern.test(detail)) return message;
  }
  return detail || fallback;
}

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
        setError(backendErrorToSpanish(err, 'Error al crear evento'));
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
        setError(backendErrorToSpanish(err, 'Error al actualizar evento'));
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
        setError(backendErrorToSpanish(err, 'Error al eliminar evento'));
        return false;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const deactivate = useCallback(
    async (id: string): Promise<OperationalEventDTO | null> => {
      setSaving(true);
      setError(null);
      try {
        await apiClient.patch(endpoints.operationalEvents.deactivate(id));
        const { data } = await apiClient.get<OperationalEventDTO>(
          endpoints.operationalEvents.byId(id)
        );
        return data;
      } catch (err: unknown) {
        setError(backendErrorToSpanish(err, 'Error al finalizar evento'));
        return null;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  return { create, update, remove, deactivate, saving, error };
}
