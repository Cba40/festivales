import { useState, useEffect } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';

export interface ZoneSubtype {
  id: string;
  zone_type_id: string;
  slug: string;
  name: string;
  icon: string | null;
  description: string | null;
  is_active: boolean;
  sort_order: number;
}

// Cache en memoria por zoneTypeId: evita re-fetch al alternar entre tipos.
const cache = new Map<string, ZoneSubtype[]>();

export function useZoneSubtypes(zoneTypeId: string | null) {
  const [data, setData] = useState<ZoneSubtype[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!zoneTypeId) {
      setData([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    const cached = cache.get(zoneTypeId);
    if (cached) {
      setData(cached);
      setIsLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    const fetchSubtypes = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data: rows } = await apiClient.get<ZoneSubtype[]>(
          endpoints.contextEngine.zoneSubtypes(),
          { params: { zone_type_id: zoneTypeId, only_active: true } },
        );
        cache.set(zoneTypeId, rows);
        if (!cancelled) {
          setData(rows);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : 'Error al cargar subtipos'
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void fetchSubtypes();
    return () => {
      cancelled = true;
    };
  }, [zoneTypeId]);

  return { data, isLoading, error };
}
