import { useCallback, useState } from 'react'
import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'
import { readThroughCache, zoneCacheKey, ZONES_TTL_MS } from '@/core/cache/memoryCache'
import { requireActiveEventId } from '@/services/activeEvent'
import { normalizeZoneStatus } from '@/utils/zoneStatus'

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
  status?: string | null
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

  const refresh = useCallback(async (force = false) => {
    setLoading(true)
    setError(null)
    try {
      const eventId = requireActiveEventId()
      const zones = await readThroughCache<ZoneRow[]>(
        zoneCacheKey(eventId),
        ZONES_TTL_MS,
        async () => {
          const { data } = await apiClient.get<ZoneRow[]>(endpoints.zones.list(eventId))
          return data
        },
        force
      )
      const cajeros = zones
        .filter((z) => z.subtipo === 'cajeros')
        // `GET /zones` no filtra (ver `Back/app/api/routes/zones.py::list_zones`:
        // devuelve todas las zonas del evento sin filtro). Baños, hidratación y
        // descanso pasan por el motor de recomendaciones, que sí excluye las
        // zonas cerradas; cajeros no, así que sin este filtro un cajero dado de
        // baja por el operador seguía apareciendo en el listado.
        //
        // Se usa `normalizeZoneStatus` y no `z.status !== 'cerrada'` porque el
        // backend puede devolver alias legacy (`cerrado`, `closed`, ...), que
        // una comparación directa no reconocería.
        .filter((z) => normalizeZoneStatus(z.status) !== 'cerrada')
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
