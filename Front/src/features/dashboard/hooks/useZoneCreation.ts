import { useState } from 'react';
import { useAppStore } from '../../../core/state/store';
import { apiClient } from '../../../core/api/client';
import { endpoints } from '../../../core/api/endpoints';
import type { Zone } from '../types';

interface CreateZoneInput {
  name: string;
  type: string;
  capacity: number;
  lat?: number;
  lng?: number;
  [key: string]: string | number | boolean | undefined;
}

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
}

/**
 * Creación de zonas contra el evento activo.
 *
 * `eventId` es opcional: si no se pasa, se usa el del store global (`activeEventId`,
 * resuelto por `useActiveEvent()` desde la jornada activa que configuró el operador).
 * Antes el default venía de `import.meta.env.VITE_EVENT_ID`.
 */
export function useZoneCreation(eventId?: string) {
  const activeEventId = useAppStore((state) => state.activeEventId);
  const resolvedEventId = eventId ?? activeEventId;
  const addZone = useAppStore((state) => state.addZone);
  const removeZone = useAppStore((state) => state.removeZone);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createZone = async (data: CreateZoneInput): Promise<ApiZone | null> => {
    setLoading(true);
    setError(null);

    const optimisticZone: Zone = {
      id: `zone-${Date.now()}`,
      name: data.name,
      type: data.type,
      saturation: 'bajo',
      status: 'activa',
      capacity: data.capacity,
      availableCapacity: data.capacity,
      lat: data.lat,
      lng: data.lng,
    };

    addZone(optimisticZone);

    try {
      const body: Record<string, unknown> = {
        name: data.name,
        type: data.type,
        capacity: data.capacity,
        latitude: data.lat,
        longitude: data.lng,
      };
      for (const key of ['disponibilidad', 'espera_min', 'calle', 'subtipo', 'tipo_culinario', 'x', 'y', 'direccion', 'horario', 'telefono', 'transporte', 'capacidad_estimada', 'es_embudo']) {
        if (data[key] !== undefined) body[key] = data[key];
      }
      if (!resolvedEventId) {
        removeZone(optimisticZone.id);
        setError('No hay evento activo configurado. Marcá una jornada como activa desde el dashboard.');
        setLoading(false);
        return null;
      }
      const res = await apiClient.post<ApiZone>(
        endpoints.zones.create(resolvedEventId),
        body
      );

      removeZone(optimisticZone.id);
      addZone({
        id: res.data.id,
        name: res.data.name,
        type: res.data.type,
        saturation: res.data.saturation as Zone['saturation'],
        status: res.data.status as Zone['status'],
        capacity: res.data.capacity,
        availableCapacity: res.data.available_capacity,
        lat: res.data.latitude ?? undefined,
        lng: res.data.longitude ?? undefined,
      });
      return res.data;
    } catch (err) {
      removeZone(optimisticZone.id);
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Error al crear la zona';
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { createZone, loading, error };
}
