import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import type { ZoneBehaviorDTO, ZoneTypeDTO } from '../types';

export function useZoneBehaviors(phaseId: string | null) {
  const [behaviors, setBehaviors] = useState<ZoneBehaviorDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!phaseId) {
      setBehaviors([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<ZoneBehaviorDTO[]>(
        `/zone-behaviors/by-phase/${phaseId}`
      );
      setBehaviors(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar comportamientos territoriales');
    } finally {
      setLoading(false);
    }
  }, [phaseId]);

  useEffect(() => { fetch(); }, [fetch]);

  return { behaviors, loading, error, refresh: fetch };
}

export function useZoneTypes() {
  const [zoneTypes, setZoneTypes] = useState<ZoneTypeDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<ZoneTypeDTO[]>(
        '/context-engine/zone-types'
      );
      setZoneTypes(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar tipos de zona');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  return { zoneTypes, loading, error, refresh: fetch };
}
