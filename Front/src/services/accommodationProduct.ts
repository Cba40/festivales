import { useState, useCallback } from 'react'
import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
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

export function useAccommodationRecommendations(
  type?: AccommodationType
) {
  const [data, setData] = useState<AccommodationRecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const userLocation = useAppStore(s => s.userLocation)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data: res } = await apiClient.get<AccommodationRecommendationResponse>(
        endpoints.products.accommodation(EVENT_ID),
        {
          params: {
            limit: 100,
            ...(userLocation
              ? { latitude: userLocation[0], longitude: userLocation[1] }
              : {}),
            ...(type ? { type } : {}),
          },
        }
      )
      setData(res)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al obtener recomendaciones de hospedaje')
    } finally {
      setLoading(false)
    }
  }, [userLocation, type])

  return { data, loading, error, refresh }
}
