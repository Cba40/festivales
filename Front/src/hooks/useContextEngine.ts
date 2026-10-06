import { useState, useCallback, useEffect, useRef } from 'react';
import { apiClient } from '../core/api/client';
import { endpoints } from '../core/api/endpoints';
import { readThroughCache, predictionCacheKey, PREDICTION_TTL_MS } from '../core/cache/memoryCache';
import { useAppStore } from '../core/state/store';

export interface ZoneStateItem {
  zone_id: string;
  operational_state: string;
  /**
   * Los cuatro campos siguientes son resultados especificos del modelo
   * especializado de la zona, y son NULL cuando no hubo modelo (ADR-004 §2.2:
   * "pueden existir o no según el modelo ejecutado"). Antes se declaraban como
   * `number`, que es una mentira: el backend manda `null` y un filtro
   * `!= null` sobre un tipo no-nullable no parece estar filtrando nada.
   *
   * `estimated_wait` es entero (minutos) en el dominio, no float.
   */
  availability: number | null;
  saturation_level: number | null;
  estimated_wait: number | null;
  confidence: number | null;
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

/**
 * Predicción territorial del evento activo.
 *
 * `eventId` es opcional y admite `null`: sin argumento usa el del store global
 * (`activeEventId`, resuelto por `useActiveEvent()` desde la jornada activa). Antes
 * el default venía de `import.meta.env.VITE_EVENT_ID`, horneado en el bundle al
 * compilar, y devolvía `''` mientras no había ID.
 *
 * El tipo declara el `null` para que `endpoints.predictions.get()` (que exige
 * `string`) no se pueda llamar sin haber decidido antes que hay evento.
 *
 * Este hook es el quesurfaced el bug "No se encontraron zonas para el evento": con
 * el ID viejo de `.env` (evento inexistente) el backend responde 404. Ahora sale
 * `No hay evento activo configurado`, que dice qué hacer.
 */
export function useTerritorialPrediction(eventId?: string | null) {
  const activeEventId = useAppStore((s) => s.activeEventId);
  const resolvedEventId = eventId ?? activeEventId;
  const [data, setData] = useState<TerritorialPredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (force = false) => {
    // Transitorio: el evento todavía no resolvió. No se setea `error` porque
    // pisaría el mensaje real de una request que sí falló.
    if (!resolvedEventId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await readThroughCache<TerritorialPredictionResponse>(
        predictionCacheKey(resolvedEventId),
        PREDICTION_TTL_MS,
        async () => {
          const { data } = await apiClient.get<TerritorialPredictionResponse>(
            endpoints.predictions.get(resolvedEventId)
          );
          return data;
        },
        force,
        true
      );
      setData(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al obtener predicciones');
    } finally {
      setLoading(false);
    }
  }, [resolvedEventId]);

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
