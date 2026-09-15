import { useState, useCallback, useRef } from 'react'
import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import { readThroughCache, productCacheKey, PRODUCT_TTL_MS } from '@/core/cache/memoryCache'
import { useAppStore } from '@/core/state/store'

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id'

export interface ZonaEstacionamientoItem {
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

export interface ParkingRecommendationResponse {
  event_id: string
  timestamp: string
  mode: string
  zonas: ZonaEstacionamientoItem[]
}

export function useParkingRecommendations() {
  const [data, setData] = useState<ParkingRecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const userLocation = useAppStore(s => s.userLocation)
  const currentZoneId = useAppStore(s => s.zones[0]?.id)

  const ctxRef = useRef({ currentZoneId, userLocation })

  const refresh = useCallback(async (force = false) => {
    setLoading(true)
    setError(null)
    try {
      const { currentZoneId: zoneIdSnapshot, userLocation: locationSnapshot } = ctxRef.current
      const params: Record<string, unknown> = {
        speed: 1.5,
        accessibility_required: false,
        limit: 4,
        current_zone_id: zoneIdSnapshot || undefined,
        user_id: '00000000-0000-0000-0000-000000000000',
        access_level: 'STANDARD',
        ...(locationSnapshot
          ? { latitude: locationSnapshot[0], longitude: locationSnapshot[1] }
          : {}),
      }
      const data = await readThroughCache<ParkingRecommendationResponse>(
        productCacheKey(EVENT_ID, 'parking', params),
        PRODUCT_TTL_MS,
        async () => {
          const { data } = await apiClient.get<ParkingRecommendationResponse>(
            endpoints.products.parking(EVENT_ID),
            { params },
          )
          return data
        },
        force,
        true
      )
      setData(data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al obtener recomendaciones de estacionamiento')
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, refresh }
}
