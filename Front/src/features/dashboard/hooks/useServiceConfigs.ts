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

/**
 * Busca el override de un subtipo para una jornada concreta.
 * GET /service-configs?event_day_id=X devuelve solo los overrides de esa
 * jornada (backend). Devuelve null si esa jornada no tiene override.
 */
export async function fetchEventDayServiceConfig(
  zoneTypeId: string,
  subtipo: string,
  eventDayId: string
): Promise<ServiceConfigDTO | null> {
  const { data: rows } = await apiClient.get<ServiceConfigDTO[]>(
    endpoints.serviceConfigs.list(),
    { params: { zone_type_id: zoneTypeId, subtipo, event_day_id: eventDayId } }
  );
  return rows.find((r) => r.event_day_id === eventDayId) ?? null;
}

export interface ResolvedServiceConfig {
  /** Fila a mostrar en el formulario y a editar/crear. */
  config: ServiceConfigDTO | null;
  /**
   * `event_day_id` contra el que hay que guardar. Es el de la jornada activa
   * cuando hay override (o cuando se quiere crearlo); `null` (default global)
   * si no hay jornada activa o si ya existe un default y no hay override.
   *
   * Refleja la precedencia del backend al LEER
   * (`_resolve_bathroom_use_rate`): override de jornada > default global.
   */
  targetEventDayId: string | null;
}

/**
 * Resuelve qué configuración editar para la jornada activa.
 *
 * Si la jornada activa tiene override, ese es el que gana (y el que hay que
 * editar). Si no, se muestra el default global como referencia visual pero se
 * prepara el payload para crear el override de la jornada, de modo que la
 * edición no pise el default global compartido por todas las jornadas.
 */
export async function resolveServiceConfigForEventDay(
  zoneTypeId: string,
  subtipo: string,
  eventDayId: string | null
): Promise<ResolvedServiceConfig> {
  if (eventDayId) {
    const override = await fetchEventDayServiceConfig(zoneTypeId, subtipo, eventDayId);
    if (override) {
      return { config: override, targetEventDayId: eventDayId };
    }
  }
  const fallback = await fetchDefaultServiceConfig(zoneTypeId, subtipo);
  return {
    config: fallback,
    targetEventDayId: eventDayId ?? null,
  };
}