import { useState, useCallback, useRef } from 'react'
import { apiClient, originHeaders, type RequestOrigin } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import { readThroughCache, productCacheKey, PRODUCT_TTL_MS } from '@/core/cache/memoryCache'
import { useAppStore } from '@/core/state/store'
import { requireActiveEventId } from '@/services/activeEvent'

// El `event_id` viene de `useActiveEvent()` (store global), no de
// `import.meta.env.VITE_EVENT_ID`: la variable de entorno se hornea en el bundle al
// compilar, así que cambiada de evento había que redeployar y un valor viejo en
// `.env` hacía pedir zonas de un evento inexistente. Se resuelve dentro de `refresh`
// y no al importar el módulo porque el store se puebla en runtime: una constante
// leída al evaluar el archivo quedaría congelada en null.

export interface ZonaGastronomicaItem {
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
  categoria: string
  lat: number | null
  lng: number | null
  referencia: string
  distancia_min: number | null
  is_nearest: boolean
}

export interface GastronomyRecommendationResponse {
  event_id: string
  timestamp: string
  mode: string
  zonas: ZonaGastronomicaItem[]
}

export async function getGastronomyRecommendations(
  eventId: string,
  params: Record<string, unknown> = {},
  requestOrigin?: RequestOrigin,
): Promise<GastronomyRecommendationResponse> {
  return readThroughCache<GastronomyRecommendationResponse>(
    productCacheKey(eventId, 'gastronomy'),
    PRODUCT_TTL_MS,
    async () => {
      const { data } = await apiClient.get<GastronomyRecommendationResponse>(
        endpoints.products.gastronomy(eventId),
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

export function useGastronomyRecommendations() {
  const [data, setData] = useState<GastronomyRecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const userLocation = useAppStore(s => s.userLocation)
  const currentZoneId = useAppStore(s => s.zones[0]?.id)

  const ctxRef = useRef({ currentZoneId, userLocation })

  const refresh = useCallback(async (force = false, requestOrigin?: RequestOrigin) => {
    setLoading(true)
    setError(null)
    try {
      const { currentZoneId: zoneIdSnapshot, userLocation: locationSnapshot } = ctxRef.current
      const params: Record<string, unknown> = {
        speed: 1.5,
        accessibility_required: false,
        limit: 6,
        current_zone_id: zoneIdSnapshot || undefined,
        user_id: '00000000-0000-0000-0000-000000000000',
        access_level: 'STANDARD',
        ...(locationSnapshot
          ? { latitude: locationSnapshot[0], longitude: locationSnapshot[1] }
          : {}),
      }
      const eventId = requireActiveEventId()
      const data = await readThroughCache<GastronomyRecommendationResponse>(
        productCacheKey(eventId, 'gastronomy'),
        PRODUCT_TTL_MS,
        async () => {
          const { data } = await apiClient.get<GastronomyRecommendationResponse>(
            endpoints.products.gastronomy(eventId),
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
      setError(err?.response?.data?.detail || 'Error al obtener recomendaciones de gastronomía')
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, refresh }
}
