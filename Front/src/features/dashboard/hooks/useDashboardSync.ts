// src/features/dashboard/hooks/useDashboardSync.ts

import { useState, useCallback } from 'react';
import { useAppStore } from '@/core/state/store';
import type { EventStateResponse } from '../types';

/**
 * Hook de sincronización del dashboard.
 * Lee zones e incidents del store global y expone refresh()
 * como placeholder para GET /events/{id}/state.
 */
export function useDashboardSync() {
  const zones = useAppStore((s) => s.zones);
  const incidents = useAppStore((s) => s.incidents);
  const setZones = useAppStore((s) => s.setZones);
  const setIncidents = useAppStore((s) => s.setIncidents);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSync, setLastSync] = useState<string | null>(null);

  /**
   * Placeholder: GET /events/{eventId}/state
   * Simula fetch con setTimeout. Listo para conectar a FastAPI.
   */
  const refresh = useCallback(async (_eventId: string = 'evt-001') => {
    setLoading(true);
    setError(null);

    try {
      // ── PLACEHOLDER API CALL ──
      // TODO: Reemplazar con fetch real a FastAPI
      // const res = await fetch(`/api/events/${eventId}/state`);
      // const data: EventStateResponse = await res.json();

      const data: EventStateResponse = await new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            zones: useAppStore.getState().zones,
            incidents: useAppStore.getState().incidents,
            timestamp: new Date().toISOString(),
          });
        }, 800);
      });

      setZones(data.zones);
      setIncidents(data.incidents);
      setLastSync(data.timestamp);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al sincronizar';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [setZones, setIncidents]);

  return {
    zones,
    incidents,
    loading,
    error,
    lastSync,
    refresh,
  };
}
