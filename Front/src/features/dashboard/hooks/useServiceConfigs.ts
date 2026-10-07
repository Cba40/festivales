import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type { ServiceConfigDTO } from '../types';

/**
 * Busca la config DEFAULT (event_day_id NULL) de un subtipo.
 * GET /service-configs sin event_day_id devuelve solo defaults (backend).
 * Devuelve null si no existe.
 */
export async function fetchDefaultServiceConfig(
  zoneTypeId: string,
  subtipo: string
): Promise<ServiceConfigDTO | null> {
  const { data: rows } = await apiClient.get<ServiceConfigDTO[]>(
    endpoints.serviceConfigs.list(),
    { params: { zone_type_id: zoneTypeId, subtipo } }
  );
  return rows.find((r) => r.event_day_id === null) ?? null;
}