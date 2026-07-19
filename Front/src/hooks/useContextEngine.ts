import { useState, useCallback, useEffect, useRef } from 'react';
import { apiClient } from '../core/api/client';
import { endpoints } from '../core/api/endpoints';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export interface ZonePredictionDTO {
  id: string;
  name: string;
  type: string;
  factores: {
    saturation: number;
    attendance: number;
    resource: number;
    priority: number;
  };
  prediccion: {
    saturation_predicha: number;
    attendance_predicha: number;
    recurso_requerido: number;
    priority_score: number;
  };
}

export interface ContextEngineResponseDTO {
  estado_actual: {
    id: string; name: string; slug: string; sort_order: number; color: string;
    description: string; is_initial: boolean; is_final: boolean;
    rules: Record<string, unknown>; created_at: string;
  } | null;
  override_activo: {
    id: string; event_day_id: string; event_state_id: string; zone_type_id: string | null;
    start_time: string; end_time: string; reason: string; created_by: string;
    is_active: boolean; created_at: string;
  } | null;
  zonas: ZonePredictionDTO[];
}

export interface ZoneStateItem {
  zone_id: string;
  operational_state: string;
  availability: number;
  saturation_level: number;
  estimated_wait: number;
  confidence: number;
  reasoning_factors: string[];
  active_restriction: string;
}

export interface TerritorialPredictionResponse {
  timestamp: string;
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

export function usePredictions(eventId: string = EVENT_ID) {
  const [data, setData] = useState<ContextEngineResponseDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (datetimeActual?: string) => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (datetimeActual) params.datetime_actual = datetimeActual;
      const { data: res } = await apiClient.get<ContextEngineResponseDTO>(
        `/events/${eventId}/prediction`, { params }
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
