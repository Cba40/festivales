import { useState, useCallback, useRef } from 'react'
import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import { readThroughCache, productCacheKey, PRODUCT_TTL_MS } from '@/core/cache/memoryCache'
import { useAppStore } from '@/core/state/store'

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id'

export type AccommodationType = 'hotel' | 'hostel' | 'camping' | 'other'

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
  params: Record<string, unknown> = {}
): Promise<AccommodationRecommendationResponse> {
  return readThroughCache<AccommodationRecommendationResponse>(
    productCacheKey(eventId, 'accommodation'),
    PRODUCT_TTL_MS,
    async () => {
      const { data } = await apiClient.get<AccommodationRecommendationResponse>(
        endpoints.products.accommodation(eventId),
        { params }
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

  const ctxRef = useRef({ userLocation })

  const refresh = useCallback(async (force = false) => {
    setLoading(true)
    setError(null)
    try {
      const { userLocation: locationSnapshot } = ctxRef.current
      const params: Record<string, unknown> = {
        limit: 100,
        ...(locationSnapshot
          ? { latitude: locationSnapshot[0], longitude: locationSnapshot[1] }
          : {}),
        ...(type ? { type } : {}),
      }
      const data = await readThroughCache<AccommodationRecommendationResponse>(
        productCacheKey(EVENT_ID, 'accommodation'),
        PRODUCT_TTL_MS,
        async () => {
          const { data } = await apiClient.get<AccommodationRecommendationResponse>(
            endpoints.products.accommodation(EVENT_ID),
            { params },
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
  }, [type])

  return { data, loading, error, refresh }
}
