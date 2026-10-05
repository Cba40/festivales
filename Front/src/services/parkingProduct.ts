import { useState, useCallback, useRef } from 'react'
import { apiClient, originHeaders, type RequestOrigin } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import { readThroughCache, productCacheKey, PRODUCT_TTL_MS } from '@/core/cache/memoryCache'
import { useAppStore } from '@/core/state/store'
import type { SaturationLevel } from '@/features/dashboard/types'

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id'

/**
 * Cuántas zonas de estacionamiento pide el hook.
 *
 * Exportada porque la pantalla la consume: `Estacionar` muestra hasta 4 tarjetas
 * y hace `zonas.slice(PARKING_LIMIT)` para el resto. Si el limit baja sin tocar
 * ese slice, la lista restante se come una zona que ya se mostró.
 */
export const PARKING_LIMIT = 4

/**
 * Minutos de distancia que se muestran cuando la zona no trae `distancia_min` ni
 * el usuario tiene GPS. Documentado para no dejarlo en un `?? 5` suelto.
 */
export const DISTANCIA_FALLBACK_MIN = 5

/**
 * Parte de clave de caché para una coordenada opcional.
 *
 * Mismo criterio que el `coordCachePart` de `emergencyProduct.ts`: redondeo a 4
 * decimales (~11 m) para que el ruido del GPS no genere entradas distintas, y
 * `'none'` para distinguir "sin coordenada" de una coordenada 0 válida.
 *
 * Duplicado de 1 línea a propósito: son dos servicios de producto
 * independientes y no conviene que Parking dependa de Emergency. Cuando
 * aparezca un tercer consumidor, esto sube a `src/utils/`.
 */
function coordCachePart(value?: number): string {
  return value == null ? 'none' : value.toFixed(4)
}

export async function getParkingRecommendations(
  eventId: string,
  params: Record<string, unknown> = {},
  requestOrigin?: RequestOrigin,
): Promise<ParkingRecommendationResponse> {
  return readThroughCache<ParkingRecommendationResponse>(
    productCacheKey(eventId, 'parking'),
    PRODUCT_TTL_MS,
    async () => {
      const { data } = await apiClient.get<ParkingRecommendationResponse>(
        endpoints.products.parking(eventId),
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

export interface ZonaEstacionamientoItem {
  zone_id: string
  name: string
  score: number
  reasoning: string[]
  saturation_level: number | null
  /**
   * Mismo vocabulario que `SaturationLevel` del dashboard y que el
   * `saturation_to_estado` del backend produce (`bajo`/`medio`/`alto`/`colapsado`).
   * Estaba declarado como `string`, que hacía que `getEstadoLabel` perdiera el
   * chequeo de exhaustividad y un estado nuevo cayera al `default` en crudo.
   */
  estado: SaturationLevel | null
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

  const refresh = useCallback(async (force = false, requestOrigin?: RequestOrigin) => {
    setLoading(true)
    setError(null)
    try {
      const { currentZoneId: zoneIdSnapshot, userLocation: locationSnapshot } = ctxRef.current
      const params: Record<string, unknown> = {
        speed: 1.5,
        accessibility_required: false,
        limit: PARKING_LIMIT,
        current_zone_id: zoneIdSnapshot || undefined,
        user_id: '00000000-0000-0000-0000-000000000000',
        access_level: 'STANDARD',
        ...(locationSnapshot
          ? { latitude: locationSnapshot[0], longitude: locationSnapshot[1] }
          : {}),
      }
      // La clave tiene que incluir todo lo que cambia el resultado: el ranking y
      // el orden de `zonas` dependen de dónde esté el usuario y de su zona actual.
      // Con la clave por evento sola, moverse dentro de los 30 s de TTL devolvía
      // la respuesta de la posición anterior.
      const cacheKey = [
        productCacheKey(EVENT_ID, 'parking'),
        zoneIdSnapshot || 'no-zone',
        coordCachePart(locationSnapshot?.[0]),
        coordCachePart(locationSnapshot?.[1]),
      ].join('|')
      const data = await readThroughCache<ParkingRecommendationResponse>(
        cacheKey,
        PRODUCT_TTL_MS,
        async () => {
          const { data } = await apiClient.get<ParkingRecommendationResponse>(
            endpoints.products.parking(EVENT_ID),
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
    } catch (err: unknown) {
      // FastAPI devuelve `detail` como string en los errores que armamos a mano y
      // como lista de objetos cuando es un fallo de validación de Pydantic. Los dos
      // casos son string en la UI; cualquier otra cosa cae al mensaje genérico.
      const detail: unknown =
        err &&
        typeof err === 'object' &&
        'response' in err &&
        (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
      setError(
        typeof detail === 'string' && detail
          ? detail
          : 'Error al obtener recomendaciones de estacionamiento'
      )
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, refresh }
}
