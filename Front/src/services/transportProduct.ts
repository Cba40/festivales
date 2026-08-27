import { useState, useCallback } from 'react'
import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import { useAppStore } from '@/core/state/store'

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id'

export interface ZonaTransporteItem {
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
  calle: string
  lat: number | null
  lng: number | null
  referencia: string
  distancia_min: number | null
  is_nearest: boolean
  line_name: string | null
  company: string | null
  next_departure: string | null
  minutes_until_next: number | null
  destination: string | null
  is_tomorrow: boolean
}

export interface TransportRecommendationResponse {
  event_id: string
  timestamp: string
  mode: string
  zonas: ZonaTransporteItem[]
}

export type TransportType = 'urbano' | 'interurbano'

export function useTransportRecommendations(
  destination?: string,
  transportType?: TransportType
) {
  const [data, setData] = useState<TransportRecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const userLocation = useAppStore(s => s.userLocation)
  const currentZoneId = useAppStore(s => s.zones[0]?.id)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data: res } = await apiClient.get<TransportRecommendationResponse>(
        endpoints.products.transport(EVENT_ID),
        {
          params: {
            speed: 1.5,
            accessibility_required: false,
            limit: 10,
            current_zone_id: currentZoneId || undefined,
            user_id: '00000000-0000-0000-0000-000000000000',
            access_level: 'STANDARD',
            ...(userLocation
              ? { latitude: userLocation[0], longitude: userLocation[1] }
              : {}),
            ...(destination ? { destination } : {}),
            ...(transportType ? { transport_type: transportType } : {}),
          },
        }
      )
      setData(res)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al obtener recomendaciones de transporte')
    } finally {
      setLoading(false)
    }
  }, [currentZoneId, userLocation, destination, transportType])

  return { data, loading, error, refresh }
}

export interface AvailableDestinationsResponse {
  destinations: string[]
}

export function useAvailableDestinations(transportType?: TransportType) {
  const [destinations, setDestinations] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await apiClient.get<AvailableDestinationsResponse>(
        endpoints.products.transportDestinations(EVENT_ID),
        {
          params: transportType ? { transport_type: transportType } : {},
        }
      )
      setDestinations(data.destinations ?? [])
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al obtener destinos de transporte')
    } finally {
      setLoading(false)
    }
  }, [transportType])

  return { destinations, loading, error, refresh }
}
