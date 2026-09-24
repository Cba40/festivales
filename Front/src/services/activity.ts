// Front/src/services/activity.ts
// Telemetría secundaria de actividad real del usuario (Analytics V2).
// ÚNICAMENTE screen_open / filter_change. NUNCA se emite desde requests,
// SWR, readThroughCache, prefetch ni efectos que reaccionan a cambios.
// Fallo del POST => error silencioso (no rompe navegación ni filtros).

import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id'

export type ActivityInteractionType = 'screen_open' | 'filter_change'

export type ActivityServiceCategory =
  | 'parking'
  | 'gastronomy'
  | 'bathroom'
  | 'hydration'
  | 'rest'
  | 'transport'
  | 'exit'
  | 'accommodation'
  | 'emergency'

// request_mode: valor semántico de la auditoría (ruta para screen_open,
// clave=valor para filter_change). Se trunca a 50 para respetar el contrato.
export function recordActivity(params: {
  interaction_type: ActivityInteractionType
  service_category: ActivityServiceCategory
  request_mode?: string
}): void {
  const requestMode = params.request_mode
    ? String(params.request_mode).slice(0, 50)
    : undefined

  apiClient
    .post(endpoints.activity.create(EVENT_ID), {
      interaction_type: params.interaction_type,
      service_category: params.service_category,
      request_mode: requestMode,
    })
    .catch(() => {})
}