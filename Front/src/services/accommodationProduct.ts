import { useState, useCallback } from 'react'
import { apiClient, originHeaders, type RequestOrigin } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import { readThroughCache, productCacheKey, PRODUCT_TTL_MS } from '@/core/cache/memoryCache'
import { useAppStore } from '@/core/state/store'
import { requireActiveEventId } from '@/services/activeEvent'
import { coordsCacheSuffix } from '@/utils/coordsCache'

export type AccommodationType = 'hotel' | 'hostel' | 'camping' | 'other'

/**
 * Cuantos alojamientos pide el hook. Es una lista de inventario, no un
 * ranking curado: el orden por defecto del backend es por nombre, asi que
 * un limite chico cortaria el catalogo sin motivo.
 */
export const ACCOMMODATION_LIMIT = 100

export interface AccommodationItem {
  id: string
  event_id: string
  name: string
  type: AccommodationType
  address: string | null
  reference: string | null
  latitude: number | null
  longitude: number | null
  phone: string | null
  website: string | null
  official_info_url: string | null
  active: boolean
  distance_km: number | null
}

export interface AccommodationRecommendationResponse {
  event_id: string
  accommodations: AccommodationItem[]
}

export async function getAccommodationRecommendations(
  eventId: string,
  params: Record<string, unknown> = {},
  requestOrigin?: RequestOrigin,
): Promise<AccommodationRecommendationResponse> {
  const cacheProductType = params.type ? `accommodation:${params.type}` : 'accommodation'
  return readThroughCache<AccommodationRecommendationResponse>(
    productCacheKey(eventId, cacheProductType),
    PRODUCT_TTL_MS,
    async () => {
      const { data } = await apiClient.get<AccommodationRecommendationResponse>(
        endpoints.products.accommodation(eventId),
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

export function useAccommodationRecommendations(
  type?: AccommodationType
) {
  const [data, setData] = useState<AccommodationRecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const userLocation = useAppStore(s => s.userLocation)

  const eventDayId = useAppStore((s) => s.eventDayId)

  const refresh = useCallback(async (force = false, requestOrigin?: RequestOrigin) => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, unknown> = {
        limit: 100,
        ...(userLocation
          ? { latitude: userLocation[0], longitude: userLocation[1] }
          : {}),
        ...(type ? { type } : {}),
        ...(eventDayId ? { event_day_id: eventDayId } : {}),
      }
      const cacheProductType = type ? `accommodation:${type}` : 'accommodation'
      const eventId = requireActiveEventId()
      const data = await readThroughCache<AccommodationRecommendationResponse>(
        [productCacheKey(eventId, cacheProductType), coordsCacheSuffix(userLocation?.[0], userLocation?.[1])]
          .filter(Boolean)
          .join('|'),
        PRODUCT_TTL_MS,
        async () => {
          const { data } = await apiClient.get<AccommodationRecommendationResponse>(
            endpoints.products.accommodation(eventId),
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
      setError(err?.response?.data?.detail || 'Error al obtener recomendaciones de hospedaje')
    } finally {
      setLoading(false)
    }
  }, [type, eventDayId, userLocation])

  return { data, loading, error, refresh }
}
