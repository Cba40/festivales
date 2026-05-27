// src/features/dashboard/hooks/useIncidentMutations.ts

import { useState, useCallback } from 'react';
import { useAppStore } from '@/core/state/store';
import type { Incident, ReportIncidentPayload } from '../types';

/**
 * Hook de mutaciones para incidentes.
 * Optimistic UI: agrega incidente al store inmediatamente,
 * simula POST a FastAPI, rollback si falla.
 */
export function useIncidentMutations() {
  const addIncident = useAppStore((s) => s.addIncident);
  const updateIncident = useAppStore((s) => s.updateIncident);
  const incidents = useAppStore((s) => s.incidents);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastCreatedId, setLastCreatedId] = useState<string | null>(null);

  /**
   * Placeholder: POST /api/incidents
   * Genera ID temporal y lo reemplaza con el del server.
   */
  const reportIncident = useCallback(
    async (data: ReportIncidentPayload) => {
      setSubmitting(true);
      setError(null);

      const tempId = `inc-temp-${Date.now()}`;

      const optimisticIncident: Incident = {
        id: tempId,
        type: data.type,
        severity: data.severity,
        description: data.description,
        status: 'abierto',
        createdAt: new Date().toISOString(),
        zoneId: data.zoneId,
      };

      // Optimistic insert
      addIncident(optimisticIncident);

      try {
        // ── PLACEHOLDER API CALL ──
        // TODO: Reemplazar con fetch real a FastAPI
        // const res = await fetch('/api/incidents', {
        //   method: 'POST',
        //   headers: { 'Content-Type': 'application/json' },
        //   body: JSON.stringify(data),
        // });
        // const created: Incident = await res.json();

        const created: Incident = await new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              ...optimisticIncident,
              id: `inc-${Date.now()}`,
            });
          }, 700);
        });

        // Reemplazar temp con ID real del server
        updateIncident(tempId, { id: created.id } as Partial<Incident>);
        setLastCreatedId(created.id);
      } catch (err) {
        // Rollback: remover el incidente optimista
        const current = useAppStore.getState().incidents;
        useAppStore.setState({
          incidents: current.filter((i) => i.id !== tempId),
        });
        const message = err instanceof Error ? err.message : 'Error al reportar incidente';
        setError(message);
      } finally {
        setSubmitting(false);
      }
    },
    [addIncident, updateIncident]
  );

  /**
   * Placeholder: PATCH /api/incidents/{id}/status
   */
  const resolveIncident = useCallback(
    async (incidentId: string) => {
      const prev = incidents.find((i) => i.id === incidentId);
      if (!prev) return;

      const previousStatus = prev.status;
      updateIncident(incidentId, { status: 'resuelto' });

      try {
        await new Promise<void>((resolve) => {
          setTimeout(resolve, 500);
        });
      } catch {
        updateIncident(incidentId, { status: previousStatus });
        setError('Error al resolver incidente');
      }
    },
    [incidents, updateIncident]
  );

  return {
    reportIncident,
    resolveIncident,
    submitting,
    error,
    lastCreatedId,
  };
}
