// src/features/dashboard/hooks/useZoneMutations.ts

import { useState, useCallback } from 'react';
import { useAppStore } from '@/core/state/store';
import type { SaturationLevel, Zone } from '../types';

/**
 * Hook de mutaciones para zonas.
 * Optimistic UI: actualiza Zustand inmediatamente,
 * simula PATCH a FastAPI, rollback si falla.
 */
export function useZoneMutations() {
  const updateZone = useAppStore((s) => s.updateZone);
  const zones = useAppStore((s) => s.zones);

  const [updating, setUpdating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  /**
   * Placeholder: PATCH /api/zones/{zoneId}/saturation
   * Optimistic update con rollback automático.
   */
  const updateSaturation = useCallback(
    async (zoneId: string, newSaturation: SaturationLevel) => {
      setUpdating(zoneId);
      setError(null);

      // Guardar estado previo para rollback
      const previousZone = zones.find((z) => z.id === zoneId);
      if (!previousZone) {
        setError('Zona no encontrada');
        setUpdating(null);
        return;
      }

      const previousSaturation = previousZone.saturation;

      // Optimistic update
      updateZone(zoneId, { saturation: newSaturation });

      try {
        // ── PLACEHOLDER API CALL ──
        // TODO: Reemplazar con fetch real a FastAPI
        // await fetch(`/api/zones/${zoneId}/saturation`, {
        //   method: 'PATCH',
        //   headers: { 'Content-Type': 'application/json' },
        //   body: JSON.stringify({ saturation: newSaturation }),
        // });

        await new Promise<void>((resolve) => {
          setTimeout(() => {
            // Simular éxito (cambiar a reject() para probar rollback)
            resolve();
          }, 600);
        });
      } catch (err) {
        // Rollback
        updateZone(zoneId, { saturation: previousSaturation });
        const message = err instanceof Error ? err.message : 'Error al actualizar saturación';
        setError(message);
      } finally {
        setUpdating(null);
      }
    },
    [zones, updateZone]
  );

  /**
   * Placeholder: PATCH /api/zones/{zoneId}/status
   */
  const updateStatus = useCallback(
    async (zoneId: string, updates: Partial<Zone>) => {
      setUpdating(zoneId);
      setError(null);

      const previousZone = zones.find((z) => z.id === zoneId);
      if (!previousZone) {
        setError('Zona no encontrada');
        setUpdating(null);
        return;
      }

      // Snapshot para rollback
      const snapshot: Partial<Zone> = {};
      for (const key of Object.keys(updates) as (keyof Zone)[]) {
        (snapshot as Record<string, unknown>)[key] = previousZone[key];
      }

      // Optimistic
      updateZone(zoneId, updates);

      try {
        await new Promise<void>((resolve) => {
          setTimeout(resolve, 600);
        });
      } catch (err) {
        updateZone(zoneId, snapshot);
        const message = err instanceof Error ? err.message : 'Error al actualizar zona';
        setError(message);
      } finally {
        setUpdating(null);
      }
    },
    [zones, updateZone]
  );

  return {
    updateSaturation,
    updateStatus,
    updating,
    error,
  };
}
