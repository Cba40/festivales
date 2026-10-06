import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type { PublicAlertsResponse } from '@/features/dashboard/types';

/**
 * Avisos y mensajes públicos del evento.
 *
 * `eventId` acepta `null` porque el store todavía no resolvió. El guard de `load`
 * es la razón por la que esta firma es `string | null`: `endpoints.products.alerts`
 * exige `string`, así que el compilador no deja construir `/events//alerts` desde
 * acá. Ese era el bug — con `''` la request salía igual, Vercel la normalizaba
 * con un 308 sin headers CORS y el error moría en el navegador sin llegar al
 * backend.
 */
export function usePublicAlerts(eventId: string | null, intervalMs = 30000) {
  const [data, setData] = useState<PublicAlertsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    // Transitorio: todavía no hay evento contra qué consultar. No se setea `error`
    // porque pisaría el mensaje real de una request que sí falló. Cuando el store
    // resuelva, `eventId` cambia, `load` se recrea y el efecto de abajo reintenta.
    if (!eventId) return;
    try {
      const res = await apiClient.get<PublicAlertsResponse>(
        endpoints.products.alerts(eventId)
      );
      setData(res.data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar avisos');
    }
  }, [eventId]);

  useEffect(() => {
    load();
    const id = setInterval(load, intervalMs);
    return () => clearInterval(id);
  }, [load, intervalMs]);

  return { data, error, refresh: load };
}