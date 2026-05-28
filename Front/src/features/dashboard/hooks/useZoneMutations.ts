import { useState } from 'react';
import { useAppStore } from '../../../core/state/store';
import { apiClient } from '../../../core/api/client';
import { endpoints } from '../../../core/api/endpoints';
import { SaturationLevel } from '../types';

const DEFAULT_EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function useZoneMutations(eventId: string = DEFAULT_EVENT_ID) {
  const updateZone = useAppStore((state) => state.updateZone);
  const zones = useAppStore((state) => state.zones);
  const [loading, setLoading] = useState(false);

  const updateSaturation = async (zoneId: string, newSaturation: SaturationLevel) => {
    const previousZone = zones.find((z) => z.id === zoneId);
    if (!previousZone) return;

    setLoading(true);
    updateZone(zoneId, { saturation: newSaturation });

    try {
      await apiClient.patch(endpoints.zones.update(eventId, zoneId), {
        saturation: newSaturation,
      });
    } catch {
      updateZone(zoneId, { saturation: previousZone.saturation });
    } finally {
      setLoading(false);
    }
  };

  return { updateSaturation, loading };
}
