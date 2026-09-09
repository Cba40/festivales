import { useCallback, useState } from 'react';
import { apiClient } from '../core/api/client';
import { endpoints } from '../core/api/endpoints';
import type {
  AuditLogEntryDTO,
  ConfigurationRecommendationDTO,
} from '../features/dashboard/types';

export function useRecommendations(statusFilter?: 'pending_review' | 'approved' | 'rejected') {
  const [recommendations, setRecommendations] = useState<ConfigurationRecommendationDTO[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRecommendations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<ConfigurationRecommendationDTO[]>(
        endpoints.analytics.recommendations(statusFilter)
      );
      setRecommendations(data ?? []);
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          (err instanceof Error ? err.message : 'Error al cargar las recomendaciones')
      );
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  return { recommendations, isLoading, error, fetchRecommendations };
}

export function useResolveRecommendation() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resolveRecommendation = useCallback(
    async (
      id: string,
      approved: boolean,
      operatorId: string,
      justification: string
    ): Promise<ConfigurationRecommendationDTO | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const { data } = await apiClient.post<ConfigurationRecommendationDTO>(
          endpoints.analytics.resolveRecommendation(id),
          {
            approved,
            operator_id: operatorId,
            justification,
          }
        );
        return data;
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data
            ?.detail ||
          (err instanceof Error ? err.message : 'Error al resolver la recomendación');
        setError(msg);
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    []
  );

  return { isSubmitting, error, resolveRecommendation };
}

export function useAuditLog() {
  const [entries, setEntries] = useState<AuditLogEntryDTO[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAuditLog = useCallback(async (recommendationId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<AuditLogEntryDTO[]>(
        endpoints.analytics.auditLog(recommendationId)
      );
      setEntries(data ?? []);
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          (err instanceof Error ? err.message : 'Error al cargar el registro de auditoría')
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { entries, isLoading, error, fetchAuditLog };
}