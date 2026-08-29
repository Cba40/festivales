import { useState, useCallback } from 'react'
import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import { useAppStore } from '@/core/state/store'

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

export async function getCities(): Promise<CityDTO[]> {
  const { data } = await apiClient.get<CityDTO[]>(endpoints.emergency.cities())
  return data
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

  const refresh = useCallback(async () => {
    if (!cityId) {
      setData(null)
      setLoading(false)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const { data: res } = await apiClient.get<EmergencyRecommendationResponse>(
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
        }
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
