import { calcularScore, getModo, getUmbralContexto } from '@/utils/decisionEngine'
import { getHoraEvento } from '@/utils/contextoEvento'
import { getEventoConfig } from '@/config/eventoConfig'

export interface ZonaEstacionamiento {
  id: string
  nombre: string
  distancia_min: number
  disponibilidad: number // 0–100
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
  referencia: string
  lat: number
  lng: number
  updatedAt: number
}

const now = Date.now()

export const zonasMock: ZonaEstacionamiento[] = [
  {
    id: 'zona-norte',
    nombre: 'Zona Norte',
    distancia_min: 6,
    disponibilidad: 15,
    estado: 'alto',
    referencia: 'Barrio Norte / Terminal',
    lat: -30.973313,
    lng: -64.088529,
    updatedAt: now - 3 * 60000
  },
  {
    id: 'zona-oeste',
    nombre: 'Zona Oeste',
    distancia_min: 8,
    disponibilidad: 45,
    estado: 'medio',
    referencia: 'Parque Autódromo',
    lat: -30.981249,
    lng: -64.099398,
    updatedAt: now - 5 * 60000
  },
  {
    id: 'zona-sur',
    nombre: 'Zona Sur',
    distancia_min: 10,
    disponibilidad: 80,
    estado: 'bajo',
    referencia: 'Predio Ferial / Costanera',
    lat: -30.985337,
    lng: -64.094209,
    updatedAt: now - 1 * 60000
  }
]

export const calcularScoreEstacionamiento = (z: ZonaEstacionamiento): number => {
  const penalizacionEstado = {
    bajo: 0,
    medio: 5,
    alto: 15,
    colapsado: 30
  }

  return (
    z.distancia_min * 1.5 +
    (100 - z.disponibilidad) * 1.0 +
    penalizacionEstado[z.estado]
  )
}

export const getZonasOrdenadas = (zonas: ZonaEstacionamiento[]) => {
  return [...zonas].sort(
    (a, b) => calcularScoreEstacionamiento(a) - calcularScoreEstacionamiento(b)
  )
}

export const getModoEstacionamiento = (zonas: ZonaEstacionamiento[]) => {
  const h = getHoraEvento()
  const umbral = getUmbralContexto(h)
  const { colapsadoThreshold, criticoThreshold } = getEventoConfig().estacionamiento

  const zonasOrdenadas = getZonasOrdenadas(zonas)
  const mejor = zonasOrdenadas[0]

  if (!mejor) return 'sin_solucion'

  if (zonas.every(z => z.disponibilidad < colapsadoThreshold)) {
    return 'sin_solucion'
  }

  if (zonas.every(z => z.disponibilidad < criticoThreshold)) {
    return 'guiar'
  }
  if (calcularScoreEstacionamiento(mejor) > umbral) return 'sin_solucion'

  return getModo(
    zonasOrdenadas.map(z => ({ estado: z.estado, score: calcularScoreEstacionamiento(z) })),
    umbral
  )
}
