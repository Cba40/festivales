import { useState } from 'react';
import { useAppStore } from '../../../core/state/store';
import { apiClient } from '../../../core/api/client';
import { endpoints } from '../../../core/api/endpoints';
import type { Incident } from '../types';

const DEFAULT_EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

interface ApiIncident {
  id: string;
  type: string;
  severity: string;
  description: string;
  status: string;
  zone_id: string | null;
  created_at: string;
}

export function useIncidentMutations(eventId: string = DEFAULT_EVENT_ID) {
  const addIncident = useAppStore((state) => state.addIncident);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reportIncident = async (data: Omit<Incident, 'id' | 'createdAt'>) => {
    setLoading(true);
    setError(null);

    try {
      const res = await apiClient.post<ApiIncident>(endpoints.incidents.create(eventId), {
        type: data.type,
        severity: data.severity,
        description: data.description,
        zone_id: data.zoneId,
      });

      addIncident({
        id: res.data.id,
        type: res.data.type,
        severity: res.data.severity as Incident['severity'],
        description: res.data.description,
        status: res.data.status as Incident['status'],
        createdAt: res.data.created_at,
        zoneId: res.data.zone_id ?? undefined,
      });
    } catch (err) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Error al reportar incidente';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return { reportIncident, loading, error };
}
