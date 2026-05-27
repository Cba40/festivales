import { useState } from 'react';
import { useAppStore } from '../../../core/state/store';
import { SaturationLevel } from '../types';

export function useZoneMutations() {
  const updateZone = useAppStore((state) => state.updateZone);
  const zones = useAppStore((state) => state.zones);
  const [loading, setLoading] = useState(false);

  const updateSaturation = async (zoneId: string, newSaturation: SaturationLevel) => {
    const previousZone = zones.find((z) => z.id === zoneId);
    if (!previousZone) return;

    setLoading(true);
    updateZone(zoneId, { saturation: newSaturation });

    try {
      await new Promise((resolve) => setTimeout(resolve, 800));
    } catch (error) {
      updateZone(zoneId, { saturation: previousZone.saturation });
      console.error('Failed to update zone saturation');
    } finally {
      setLoading(false);
    }
  };

  return { updateSaturation, loading };
}
