import { useState, useCallback } from 'react';
import { useAppStore } from '../../../core/state/store';
import { apiClient } from '../../../core/api/client';
import { endpoints } from '../../../core/api/endpoints';
import { readThroughCache, zoneCacheKey, ZONES_TTL_MS } from '../../../core/cache/memoryCache';
import type { Zone } from '../types';

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
  espera_min: number | null;
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
    espera_min: api.espera_min ?? undefined,
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

/**
 * Sincroniza las zonas del evento activo.
 *
 * `eventId` es opcional: sin argumento usa el del store global (`activeEventId`,
 * resuelto por `useActiveEvent()` desde la jornada activa). Antes el default venía
 * de `import.meta.env.VITE_EVENT_ID`, horneado en el bundle al compilar.
 */
export function useDashboardSync(eventId?: string) {
  const activeEventId = useAppStore((state) => state.activeEventId);
  const resolvedEventId = eventId ?? activeEventId;
  const setZones = useAppStore((state) => state.setZones);
  const zones = useAppStore((state) => state.zones);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (force = false) => {
    // Sin evento resuelto todavía (o sin jornada configurada) no hay contra qué
    // consultar. Se sale sin `setError` porque es un estado transitorio esperado:
    // `refresh` corre en varios mounts y volver a setear el error en cada uno
    // pisaría el mensaje real de una request que sí falló.
    if (!resolvedEventId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const zones = await readThroughCache<ApiZone[]>(
        zoneCacheKey(resolvedEventId),
        ZONES_TTL_MS,
        async () => {
          const zonesRes = await apiClient.get<ApiZone[]>(
            endpoints.zones.list(resolvedEventId)
          );
          return zonesRes.data;
        },
        force
      );
      setZones(zones.map(mapZone));
    } catch (err) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Error al sincronizar dashboard';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [resolvedEventId, setZones]);

  return { zones, loading, error, refresh };
}
