import { useState, useCallback } from 'react'
import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import { useAppStore } from '@/core/state/store'

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id'

export interface ZonaSaludItem {
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

export interface HealthRecommendationResponse {
  event_id: string
  timestamp: string
  mode: string
  zonas: ZonaSaludItem[]
}

export function useHealthRecommendations() {
  const [data, setData] = useState<HealthRecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const userLocation = useAppStore(s => s.userLocation)
  const currentZoneId = useAppStore(s => s.zones[0]?.id)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data: res } = await apiClient.get<HealthRecommendationResponse>(
        endpoints.products.health(EVENT_ID),
        {
          params: {
            speed: 1.5,
            accessibility_required: false,
            limit: 10,
            current_zone_id: currentZoneId || undefined,
            // TODO:
            // Reemplazar por el identificador real del visitante
            // cuando exista contexto de autenticación.
            user_id: '00000000-0000-0000-0000-000000000000',
            access_level: 'STANDARD',
          },
        }
      )
      setData(res)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al obtener recomendaciones de salud')
    } finally {
      setLoading(false)
    }
  }, [currentZoneId])

  return { data, loading, error, refresh }
}
