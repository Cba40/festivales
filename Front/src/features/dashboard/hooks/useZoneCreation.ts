import { useState } from 'react';
import { useAppStore } from '../../../core/state/store';
import type { Zone } from '../types';

interface CreateZoneInput {
  name: string;
  type: string;
  capacity: number;
  lat?: number;
  lng?: number;
}

export function useZoneCreation() {
  const addZone = useAppStore((state) => state.addZone);
  const removeZone = useAppStore((state) => state.removeZone);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createZone = async (data: CreateZoneInput) => {
    setLoading(true);
    setError(null);

    const newZone: Zone = {
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

    addZone(newZone);

    try {
      await new Promise((resolve) => setTimeout(resolve, 800));
      const shouldFail = Math.random() < 0.1;
      if (shouldFail) {
        throw new Error('Error simulado del servidor');
      }
    } catch (err) {
      removeZone(newZone.id);
      setError(err instanceof Error ? err.message : 'Error al crear la zona');
    } finally {
      setLoading(false);
    }
  };

  return { createZone, loading, error };
}
