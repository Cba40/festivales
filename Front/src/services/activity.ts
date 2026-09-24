// Front/src/services/activity.ts
// Telemetría secundaria de actividad real del usuario (Analytics V2).
// ÚNICAMENTE screen_open / filter_change. NUNCA se emite desde requests,
// SWR, readThroughCache, prefetch ni efectos que reaccionan a cambios.
// Fallo del POST => error silencioso (no rompe navegación ni filtros).

import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'

const EVENT_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const configuredEventId: string = import.meta.env.VITE_EVENT_ID

// El endpoint /activity exige un UUID estricto: sin event_id válido no se
// registra nada (y no se intenta enviar un identificador ficticio).
const EVENT_ID: string | null =
  configuredEventId && EVENT_ID_PATTERN.test(configuredEventId)
    ? configuredEventId
    : null

let invalidEventIdWarned = false

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
  if (!EVENT_ID) {
    if (!invalidEventIdWarned) {
      invalidEventIdWarned = true
      console.warn(
        '[activity] VITE_EVENT_ID ausente o no es un UUID válido: no se registra actividad de usuario.'
      )
    }
    return
  }

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