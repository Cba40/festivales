import { useState, useCallback, useRef } from 'react'
import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import { useAppStore } from '@/core/state/store'

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id'

// Canónica RFC-EXIT-V1 / migración c9d3e7f1a5b8 (zones.transporte)
export type TransporteMode = 'peatonal' | 'vehicular' | 'transporte'

export interface ExitDestinationItem {
  id: string
  name: string
  active: boolean
}

export interface ExitZoneItem {
  zone_id: string
  name: string
  transporte: string
  lat: number | null
  lng: number | null
  status: string
  is_nearest: boolean
  destinations: ExitDestinationItem[]
}

export interface ExitRecommendationResponse {
  event_id: string
  timestamp: string
  zonas: ExitZoneItem[]
}

export function useExitRecommendations(
  destinationId?: string,
  mode?: TransporteMode
) {
  const [data, setData] = useState<ExitRecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const userLocation = useAppStore(s => s.userLocation)

  const ctxRef = useRef({ userLocation })

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { userLocation: locationSnapshot } = ctxRef.current
      const { data: res } = await apiClient.get<ExitRecommendationResponse>(
        endpoints.products.exit(EVENT_ID),
        {
          params: {
            ...(destinationId ? { destination_id: destinationId } : {}),
            ...(mode ? { mode } : {}),
            ...(locationSnapshot
              ? { latitude: locationSnapshot[0], longitude: locationSnapshot[1] }
              : {}),
          },
        }
      )
      setData(res)
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      setError(detail || 'Error al obtener salidas')
    } finally {
      setLoading(false)
    }
  }, [destinationId, mode])

  return { data, loading, error, refresh }
}
