import { useState, useCallback } from 'react'
import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import { useAppStore } from '@/core/state/store'

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id'

export interface ZonaHidratacionItem {
  zone_id: string
  name: string
  score: number
  reasoning: string[]
  saturation_level: number
  estado: string
  availability: number
  estimated_wait: number
  confidence: number
  active_restriction: string
  operational_state: string
  lat: number | null
  lng: number | null
  referencia: string
  distancia_min: number | null
}

export interface HydrationRecommendationResponse {
  event_id: string
  timestamp: string
  mode: string
  zonas: ZonaHidratacionItem[]
}

export function useHydrationRecommendations() {
  const [data, setData] = useState<HydrationRecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const userLocation = useAppStore(s => s.userLocation)
  const currentZoneId = useAppStore(s => s.zones[0]?.id)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data: res } = await apiClient.get<HydrationRecommendationResponse>(
        endpoints.products.hydration(EVENT_ID),
        {
          params: {
            speed: 1.5,
            accessibility_required: false,
            limit: 10,
            current_zone_id: currentZoneId || undefined,
            user_id: '00000000-0000-0000-0000-000000000000',
            access_level: 'STANDARD',
          },
        }
      )
      setData(res)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al obtener recomendaciones de hidratación')
    } finally {
      setLoading(false)
    }
  }, [currentZoneId])

  return { data, loading, error, refresh }
}
