import { useState } from 'react';
import { useAppStore } from '../../../core/state/store';
import type { Zone } from '../types';

export function useZoneConfigMutations() {
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
      await new Promise((resolve) => setTimeout(resolve, 800));
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

    try {
      await new Promise((resolve) => setTimeout(resolve, 800));
    } catch {
      useAppStore.getState().updateZoneConfig(id, previous as Partial<Zone>);
    } finally {
      setLoading(false);
    }
  };

  return { deleteZone, updateZone, loading };
}
