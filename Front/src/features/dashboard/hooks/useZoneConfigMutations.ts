import { useState } from 'react';
import { useAppStore } from '../../../core/state/store';
import { apiClient } from '../../../core/api/client';
import { endpoints } from '../../../core/api/endpoints';
import type { Zone } from '../types';

const DEFAULT_EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function useZoneConfigMutations(eventId: string = DEFAULT_EVENT_ID) {
  const { removeZone, updateZoneConfig, zones } = useAppStore();
  const [loading, setLoading] = useState(false);

  const deleteZone = async (id: string): Promise<boolean> => {
    const confirmed = window.confirm(
      '¿Estás seguro de eliminar esta zona? Esta acción no se puede deshacer.'
    );
    if (!confirmed) return false;

    const zoneToRemove = zones.find((z) => z.id === id);
    if (!zoneToRemove) return false;

    setLoading(true);
    removeZone(id);

    try {
      await apiClient.delete(endpoints.zones.delete(eventId, id));
    } catch {
      useAppStore.getState().addZone(zoneToRemove);
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

  return { deleteZone, updateZone, patchZoneFields, loading };
}
