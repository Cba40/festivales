import { useState, useCallback } from 'react';
import { apiClient } from '../core/api/client';
import { endpoints } from '../core/api/endpoints';
import type {
  OperationalObservationCreatePayload,
  OperationalObservationDTO,
  OperationalObservationUpdatePayload,
} from '../features/dashboard/types';

interface UseOperationalObservationsResult {
  observations: OperationalObservationDTO[];
  isLoading: boolean;
  isSubmitting: boolean;
  isUpdating: boolean;
  error: string | null;
  fetchObservations: () => Promise<void>;
  createObservation: (
    payload: OperationalObservationCreatePayload
  ) => Promise<OperationalObservationDTO | null>;
  updateObservation: (
    id: string,
    payload: OperationalObservationUpdatePayload
  ) => Promise<OperationalObservationDTO | null>;
}

const MAX_LIST_ITEMS = 20;

export function useOperationalObservations(): UseOperationalObservationsResult {
  const [observations, setObservations] = useState<OperationalObservationDTO[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchObservations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<OperationalObservationDTO[]>(
        endpoints.operationalObservations.list
      );
      const sorted = [...data].sort(
        (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
      setObservations(sorted.slice(0, MAX_LIST_ITEMS));
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err instanceof Error ? err.message : 'Error al cargar observaciones');
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createObservation = useCallback(
    async (payload: OperationalObservationCreatePayload) => {
      setIsSubmitting(true);
      setError(null);
      try {
        const { data } = await apiClient.post<OperationalObservationDTO>(
          endpoints.operationalObservations.list,
          payload
        );
        setObservations((prev) =>
          [...prev, data]
            .sort(
              (a, b) =>
                new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
            )
            .slice(0, MAX_LIST_ITEMS)
        );
        return data;
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data
            ?.detail ||
          (err instanceof Error ? err.message : 'Error al registrar la observación');
        setError(msg);
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    []
  );

  const updateObservation = useCallback(
    async (id: string, payload: OperationalObservationUpdatePayload) => {
      setIsUpdating(true);
      setError(null);
      try {
        const { data } = await apiClient.patch<OperationalObservationDTO>(
          endpoints.operationalObservations.update(id),
          payload
        );
        // Se reemplaza la fila en lugar de recargar la lista: el PATCH devuelve
        // el registro completo ya con los warnings recalculados, y las notas y
        // la densidad corregidas. Volver a pedir la lista entera seria un viaje
        // extra por algo que ya tenemos en la respuesta.
        setObservations((prev) =>
          prev.map((obs) => (obs.id === id ? data : obs))
        );
        return data;
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data
            ?.detail ||
          (err instanceof Error
            ? err.message
            : 'Error al corregir la observación');
        setError(msg);
        return null;
      } finally {
        setIsUpdating(false);
      }
    },
    []
  );

  return {
    observations,
    isLoading,
    isSubmitting,
    isUpdating,
    error,
    fetchObservations,
    createObservation,
    updateObservation,
  };
}