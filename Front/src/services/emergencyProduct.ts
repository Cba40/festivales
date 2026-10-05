import { useState, useCallback } from 'react'
import { apiClient, originHeaders, type RequestOrigin } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import { readThroughCache } from '@/core/cache/memoryCache'
import { useAppStore } from '@/core/state/store'

export const EMERGENCY_TTL_MS = 60_000

export function emergencyCacheKey(...parts: string[]): string {
  return `emergency:${parts.join(':')}`
}

/**
 * Parte de clave de caché para una coordenada opcional.
 *
 * Tiene que ir en la clave porque la respuesta depende de ella: el backend ordena
 * por distancia Haversine cuando recibe coordenadas y alfabéticamente cuando no.
 * Son dos respuestas distintas y no pueden compartir entrada.
 *
 * - Se redondea a 4 decimales (~11 m) para que dos lecturas del mismo GPS que
 *   difieren en metros no generen entradas distintas.
 * - `0` es una coordenada válida, así que la ausencia se marca con `'none'` en vez
 *   de dejar `undefined` en el join: `sin-coordenadas` y `lat=0,lng=0` son
 *   respuestas distintas.
 */
function coordCachePart(value?: number): string {
  return value == null ? 'none' : value.toFixed(4)
}

export type EmergencyType =
  | 'policia'
  | 'bomberos'
  | 'salud'
  | 'defensa_civil'
  | 'numero_emergencia'
  | 'otro'

export interface EmergencyItem {
  id: string
  name: string
  type: EmergencyType
  phone: string | null
  emergency_number: string | null
  address: string | null
  reference: string | null
  latitude: number | null
  longitude: number | null
  services: string | null
  schedule: string | null
  active: boolean
  distance_km: number | null
}

export interface EmergencyRecommendationResponse {
  emergencies: EmergencyItem[]
}

export interface CityDTO {
  id: string
  name: string
  province: string | null
  country: string
}

export type ProtocolContext = 'festival' | 'transporte' | 'hospedaje'

export interface ProtocolDTO {
  id: string
  context: ProtocolContext
  title: string
  description: string | null
  icon: string
  steps: string[]
  priority: number
  order: number
  target_type: EmergencyType | null
  active: boolean
}

export interface EmergencyProtocolResponse {
  context: ProtocolContext
  protocols: ProtocolDTO[]
}

export async function getCities(requestOrigin?: RequestOrigin): Promise<CityDTO[]> {
  return readThroughCache<CityDTO[]>(
    emergencyCacheKey('cities'),
    EMERGENCY_TTL_MS,
    async () => {
      const { data } = await apiClient.get<CityDTO[]>(endpoints.emergency.cities(), {
        ...(requestOrigin ? { headers: originHeaders(requestOrigin) } : {}),
      })
      return data
    },
    false,
    true
  )
}

export async function getProtocols(context: string, requestOrigin?: RequestOrigin): Promise<ProtocolDTO[]> {
  return readThroughCache<ProtocolDTO[]>(
    emergencyCacheKey('protocols', context),
    EMERGENCY_TTL_MS,
    async () => {
      const { data } = await apiClient.get<EmergencyProtocolResponse>(
        endpoints.emergency.protocols(context),
        {
          ...(requestOrigin ? { headers: originHeaders(requestOrigin) } : {}),
        }
      )
      return data.protocols
    },
    false,
    true
  )
}

export async function getRecommendedResource(
  targetType: string,
  cityId: string,
  lat?: number,
  lng?: number
): Promise<EmergencyItem | null> {
  return readThroughCache<EmergencyItem | null>(
    emergencyCacheKey(
      'recommended',
      targetType,
      cityId,
      coordCachePart(lat),
      coordCachePart(lng)
    ),
    EMERGENCY_TTL_MS,
    async () => {
      try {
        const { data } = await apiClient.get<EmergencyItem>(
          endpoints.emergency.recommendedResource(targetType, cityId, lat, lng)
        )
        return data
      } catch (err) {
        const status: unknown =
          err &&
          typeof err === 'object' &&
          'response' in err &&
          (err as { response?: { status?: unknown } }).response?.status
        if (status === 404) throw err
        return null
      }
    },
    false,
    true
  )
}

export async function getEmergencies(
  cityId: string,
  limit = 20,
  type?: EmergencyType | 'todos'
): Promise<EmergencyRecommendationResponse> {
  const { data } = await apiClient.get<EmergencyRecommendationResponse>(
    endpoints.emergency.list(),
    {
      params: {
        city_id: cityId,
        limit,
        ...(type && type !== 'todos' ? { type } : {}),
      },
    }
  )
  return data
}

export function useEmergencyRecommendations(
  cityId?: string,
  type?: EmergencyType | 'todos'
) {
  const [data, setData] = useState<EmergencyRecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const userLocation = useAppStore(s => s.userLocation)

  const refresh = useCallback(async (requestOrigin?: RequestOrigin) => {
    if (!cityId) {
      setData(null)
      setLoading(false)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await readThroughCache<EmergencyRecommendationResponse>(
        emergencyCacheKey(
          'recommendation',
          type || 'todos',
          cityId,
          coordCachePart(userLocation?.[0]),
          coordCachePart(userLocation?.[1])
        ),
        EMERGENCY_TTL_MS,
        async () => {
          const { data } = await apiClient.get<EmergencyRecommendationResponse>(
            endpoints.emergency.list(),
            {
              params: {
                city_id: cityId,
                limit: 20,
                ...(type && type !== 'todos' ? { type } : {}),
                ...(userLocation
                  ? { latitude: userLocation[0], longitude: userLocation[1] }
                  : {}),
              },
              ...(requestOrigin ? { headers: originHeaders(requestOrigin) } : {}),
            }
          )
          return data
        },
        false,
        true
      )
      setData(res)
    } catch (err) {
      const detail: unknown =
        err &&
        typeof err === 'object' &&
        'response' in err &&
        (err as { response?: { data?: { detail?: unknown } } }).response?.data
          ?.detail
      setError(
        typeof detail === 'string' && detail
          ? detail
          : 'Error al obtener las emergencias de la ciudad'
      )
    } finally {
      setLoading(false)
    }
  }, [cityId, type, userLocation])

  return { data, loading, error, refresh }
}
