import { useState, useCallback } from 'react';
import { useAppStore } from '../../../core/state/store';
import { apiClient } from '../../../core/api/client';
import { endpoints } from '../../../core/api/endpoints';
import type { Zone } from '../types';

const DEFAULT_EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

interface ApiZone {
  id: string;
  name: string;
  type: string;
  saturation: string;
  status: string;
  capacity: number;
  available_capacity: number;
  latitude: number | null;
  longitude: number | null;
  disponibilidad: number | null;
  distancia_min: number | null;
  espera_min: number | null;
  referencia: string | null;
  calle: string | null;
  subtipo: string | null;
  tipo_culinario: string | null;
  x: number | null;
  y: number | null;
  direccion: string | null;
  horario: string | null;
  telefono: string | null;
  servicios: string | null;
  transporte: string | null;
  capacidad_estimada: number | null;
  es_embudo: boolean | null;
}

function mapZone(api: ApiZone): Zone {
  return {
    id: api.id,
    name: api.name,
    type: api.type,
    saturation: api.saturation as Zone['saturation'],
    status: api.status as Zone['status'],
    capacity: api.capacity,
    availableCapacity: api.available_capacity,
    lat: api.latitude ?? undefined,
    lng: api.longitude ?? undefined,
    disponibilidad: api.disponibilidad ?? undefined,
    distancia_min: api.distancia_min ?? undefined,
    espera_min: api.espera_min ?? undefined,
    referencia: api.referencia ?? undefined,
    calle: api.calle ?? undefined,
    subtipo: api.subtipo ?? undefined,
    tipo_culinario: api.tipo_culinario ?? undefined,
    x: api.x ?? undefined,
    y: api.y ?? undefined,
    direccion: api.direccion ?? undefined,
    horario: api.horario ?? undefined,
    telefono: api.telefono ?? undefined,
    servicios: api.servicios ?? undefined,
    transporte: api.transporte ?? undefined,
    capacidad_estimada: api.capacidad_estimada ?? undefined,
    es_embudo: api.es_embudo ?? undefined,
  };
}

export function useDashboardSync(eventId: string = DEFAULT_EVENT_ID) {
  const setZones = useAppStore((state) => state.setZones);
  const zones = useAppStore((state) => state.zones);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const zonesRes = await apiClient.get<ApiZone[]>(endpoints.zones.list(eventId));
      setZones(zonesRes.data.map(mapZone));
    } catch (err) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Error al sincronizar dashboard';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [eventId, setZones]);

  return { zones, loading, error, refresh };
}
