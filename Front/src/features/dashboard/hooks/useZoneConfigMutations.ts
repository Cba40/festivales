import { useState } from 'react';
import { useAppStore } from '../../../core/state/store';
import { apiClient } from '../../../core/api/client';
import { endpoints } from '../../../core/api/endpoints';
import type { Zone } from '../types';

const DEFAULT_EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function useZoneConfigMutations(eventId: string = DEFAULT_EVENT_ID) {
  const { removeZone, updateZoneConfig, zones } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // La confirmación visual (ConfirmDialog) la maneja el componente: este método
  // solo ejecuta el borrado optimista contra el store y contra la API.
  const deleteZone = async (id: string): Promise<boolean> => {
    const zoneToRemove = zones.find((z) => z.id === id);
    if (!zoneToRemove) return false;

    setLoading(true);
    setError(null);
    removeZone(id);

    try {
      await apiClient.delete(endpoints.zones.delete(eventId, id));
    } catch {
      useAppStore.getState().addZone(zoneToRemove);
      setError('No se pudo eliminar la zona. Intentá de nuevo.');
      return false;
    } finally {
      setLoading(false);
    }

    return true;
  };

  const updateZone = async (id: string, updates: Partial<Zone>) => {
    const previous = zones.find((z) => z.id === id);
    if (!previous) return;

    setLoading(true);
    setError(null);
    updateZoneConfig(id, updates);

    const body: Record<string, unknown> = {};
    if (updates.name !== undefined) body.name = updates.name;
    if (updates.type !== undefined) body.type = updates.type;
    if (updates.capacity !== undefined) body.capacity = updates.capacity;
    if (updates.lat !== undefined) body.latitude = updates.lat;
    if (updates.lng !== undefined) body.longitude = updates.lng;

    try {
      await apiClient.put(endpoints.zones.updateConfig(eventId, id), body);
    } catch {
      useAppStore.getState().updateZoneConfig(id, previous as Partial<Zone>);
      setError('No se pudo actualizar la zona. Intentá de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  // PATCH /events/{eventId}/zones/{zoneId}: acepta campos que PUT /config no
  // admite (p. ej. subtipo, vía ZoneUpdateRequest).
  const patchZoneFields = async (
    id: string,
    fields: Record<string, string | number | boolean | null>
  ): Promise<boolean> => {
    try {
      await apiClient.patch(endpoints.zones.update(eventId, id), fields);
      return true;
    } catch {
      return false;
    }
  };

  return { deleteZone, updateZone, patchZoneFields, loading, error };
}