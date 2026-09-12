import { useCallback, useState } from 'react';
import { apiClient } from '../core/api/client';
import { endpoints } from '../core/api/endpoints';
import type { EvaluationResponse } from '../features/dashboard/types';

export function useMetricsEvaluation() {
  const [data, setData] = useState<EvaluationResponse | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const evaluate = useCallback(async (eventDayId: string, phaseId: string) => {
    setIsEvaluating(true);
    setError(null);
    try {
      const { data: response } = await apiClient.post<EvaluationResponse>(
        endpoints.analytics.evaluate,
        { event_day_id: eventDayId, phase_id: phaseId }
      );
      setData(response);
      return response;
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ||
        (err instanceof Error ? err.message : 'Error al evaluar métricas');
      setError(msg);
      setData(null);
      return null;
    } finally {
      setIsEvaluating(false);
    }
  }, []);

  return { data, isEvaluating, error, evaluate };
}