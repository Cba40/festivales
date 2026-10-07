import { useState, useCallback, useRef } from 'react'
import { apiClient, originHeaders, type RequestOrigin } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import { readThroughCache, productCacheKey, PRODUCT_TTL_MS } from '@/core/cache/memoryCache'
import { useAppStore } from '@/core/state/store'
import { requireActiveEventId } from '@/services/activeEvent'

/**
 * Cuántas zonas de baño pide el hook.
 *
 * El backend selecciona sugerencias curadas por rol para `servicios`
 * (`WeightedScoringStrategy._select_curated_options`) y devuelve como máximo 4:
 * más lugares libres, mejor balance disponibilidad/distancia, más cerca de vos
 * y cerca del epicentro. Pedir más de 4 no agrega información: el backend
 * trunca al set curado, no al `limit`.
 */
export const BATHROOM_LIMIT = 4

export interface ZonaSanitaryItem {
  zone_id: string
  name: string
  score: number
  reasoning: string[]
  saturation_level: number | null
  estado: string | null
  availability: number | null
  estimated_wait: number | null
  confidence: number | null
  active_restriction: string
  operational_state: string
  lat: number | null
  lng: number | null
  referencia: string
  distancia_min: number | null
  is_nearest: boolean
}

export interface BathroomRecommendationResponse {
  event_id: string
  timestamp: string
  mode: string
  zonas: ZonaSanitaryItem[]
}

export async function getBathroomRecommendations(
  eventId: string,
  params: Record<string, unknown> = {},
  requestOrigin?: RequestOrigin,
): Promise<BathroomRecommendationResponse> {
  return readThroughCache<BathroomRecommendationResponse>(
    productCacheKey(eventId, 'bathroom'),
    PRODUCT_TTL_MS,
    async () => {
      const { data } = await apiClient.get<BathroomRecommendationResponse>(
        endpoints.products.bathroom(eventId),
        {
          params,
          ...(requestOrigin ? { headers: originHeaders(requestOrigin) } : {}),
        },
      )
      return data
    },
    false,
    true
  )
}

export function useBathroomRecommendations() {
  const [data, setData] = useState<BathroomRecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const userLocation = useAppStore(s => s.userLocation)
  const currentZoneId = useAppStore(s => s.zones[0]?.id)

  const eventDayId = useAppStore((s) => s.eventDayId)
  const ctxRef = useRef({ currentZoneId, userLocation })

  const refresh = useCallback(async (force = false, requestOrigin?: RequestOrigin) => {
    setLoading(true)
    setError(null)
    try {
      const { currentZoneId: zoneIdSnapshot, userLocation: locationSnapshot } = ctxRef.current
      const params: Record<string, unknown> = {
        speed: 1.5,
        accessibility_required: false,
        limit: BATHROOM_LIMIT,
        current_zone_id: zoneIdSnapshot || undefined,
        user_id: '00000000-0000-0000-0000-000000000000',
        access_level: 'STANDARD',
        ...(eventDayId ? { event_day_id: eventDayId } : {}),
        ...(locationSnapshot
          ? { latitude: locationSnapshot[0], longitude: locationSnapshot[1] }
          : {}),
      }
      const eventId = requireActiveEventId()
      const data = await readThroughCache<BathroomRecommendationResponse>(
        productCacheKey(eventId, 'bathroom'),
        PRODUCT_TTL_MS,
        async () => {
          const { data } = await apiClient.get<BathroomRecommendationResponse>(
            endpoints.products.bathroom(eventId),
            {
              params,
              ...(requestOrigin ? { headers: originHeaders(requestOrigin) } : {}),
            },
          )
          return data
        },
        force,
        true
      )
      setData(data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al obtener recomendaciones de baños')
    } finally {
      setLoading(false)
    }
  }, [eventDayId])

  return { data, loading, error, refresh }
}
