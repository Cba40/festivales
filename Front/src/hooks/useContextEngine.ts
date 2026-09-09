import { useState, useCallback, useEffect, useRef } from 'react';
import { apiClient } from '../core/api/client';
import { endpoints } from '../core/api/endpoints';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export interface ZoneStateItem {
  zone_id: string;
  operational_state: string;
  availability: number;
  saturation_level: number;
  estimated_wait: number;
  confidence: number;
  reasoning_factors: string[];
  active_restriction: string;
  type?: string;
  subtipo?: string | null;
}

export interface TerritorialPredictionResponse {
  timestamp: string;
  knowledge_model_version_id: string | null;
  active_phase_id: string;
  active_event_day_phase_id: string;
  zone_states: ZoneStateItem[];
}

export function useTerritorialPrediction(eventId: string = EVENT_ID) {
  const [data, setData] = useState<TerritorialPredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: res } = await apiClient.get<TerritorialPredictionResponse>(
        endpoints.predictions.get(eventId)
      );
      setData(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al obtener predicciones');
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  return { data, loading, error, refresh };
}

export function useAutoRefresh(fn: () => void, intervalMs: number, active: boolean) {
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => fnRef.current(), intervalMs);
    return () => clearInterval(id);
  }, [active, intervalMs]);
}
