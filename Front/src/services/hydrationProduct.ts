import { useState, useCallback } from 'react'
import { apiClient, originHeaders, type RequestOrigin } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import { readThroughCache, productCacheKey, PRODUCT_TTL_MS } from '@/core/cache/memoryCache'
import { useAppStore } from '@/core/state/store'
import { requireActiveEventId } from '@/services/activeEvent'
import { coordsCacheSuffix } from '@/utils/coordsCache'

/**
 * Cuantas zonas pide el hook: los puntos de hidratación.
 *
 * El backend usa seleccion curada por rol para `servicios`, asi que el set
 * util ya viene recortado a 4; pedir mas no agrega informacion.
 */
export const HYDRATION_LIMIT = 4

export interface ZonaHidratacionItem {
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

export interface HydrationRecommendationResponse {
  event_id: string
  timestamp: string
  mode: string
  zonas: ZonaHidratacionItem[]
}

export async function getHydrationRecommendations(
  eventId: string,
  params: Record<string, unknown> = {},
  requestOrigin?: RequestOrigin,
): Promise<HydrationRecommendationResponse> {
  return readThroughCache<HydrationRecommendationResponse>(
    productCacheKey(eventId, 'hydration'),
    PRODUCT_TTL_MS,
    async () => {
      const { data } = await apiClient.get<HydrationRecommendationResponse>(
        endpoints.products.hydration(eventId),
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

export function useHydrationRecommendations() {
  const [data, setData] = useState<HydrationRecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const userLocation = useAppStore(s => s.userLocation)
  const currentZoneId = useAppStore(s => s.zones[0]?.id)

  const eventDayId = useAppStore((s) => s.eventDayId)

  const refresh = useCallback(async (force = false, requestOrigin?: RequestOrigin) => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, unknown> = {
        speed: 1.5,
        accessibility_required: false,
        limit: HYDRATION_LIMIT,
        current_zone_id: currentZoneId || undefined,
        user_id: '00000000-0000-0000-0000-000000000000',
        access_level: 'STANDARD',
        ...(eventDayId ? { event_day_id: eventDayId } : {}),
        ...(userLocation
          ? { latitude: userLocation[0], longitude: userLocation[1] }
          : {}),
      }
      const eventId = requireActiveEventId()
      const data = await readThroughCache<HydrationRecommendationResponse>(
        [productCacheKey(eventId, 'hydration'), coordsCacheSuffix(userLocation?.[0], userLocation?.[1])]
          .filter(Boolean)
          .join('|'),
        PRODUCT_TTL_MS,
        async () => {
          const { data } = await apiClient.get<HydrationRecommendationResponse>(
            endpoints.products.hydration(eventId),
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
      setError(err?.response?.data?.detail || 'Error al obtener recomendaciones de hidratación')
    } finally {
      setLoading(false)
    }
  }, [eventDayId, currentZoneId, userLocation])

  return { data, loading, error, refresh }
}
