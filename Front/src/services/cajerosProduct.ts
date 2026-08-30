import { useCallback, useState } from 'react'
import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id'

export interface CajeroItem {
  zone_id: string
  name: string
  estado: null
  saturation_level: null
  confidence: null
  estimated_wait: null
  availability: null
  lat: number | null
  lng: number | null
  referencia: string
  distancia_min: number | null
  is_nearest: boolean
}

interface ZoneRow {
  id: string
  name: string
  latitude?: number | null
  longitude?: number | null
  calle?: string | null
  direccion?: string | null
  subtipo?: string | null
  capacity?: number | null
  capacidad_estimada?: number | null
}

export function useCajeros() {
  const [data, setData] = useState<CajeroItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data: zones } = await apiClient.get<ZoneRow[]>(
        endpoints.zones.list(EVENT_ID)
      )
      const cajeros = zones
        .filter((z) => z.subtipo === 'cajeros')
        .map((z) => ({
          zone_id: z.id,
          name: z.name,
          estado: null,
          saturation_level: null,
          confidence: null,
          estimated_wait: null,
          availability: null,
          lat: z.latitude ?? null,
          lng: z.longitude ?? null,
          referencia: z.calle || z.direccion || '',
          distancia_min: null,
          is_nearest: false,
        }))
      setData(cajeros)
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : 'Error al obtener cajeros'
      )
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, refresh }
}
