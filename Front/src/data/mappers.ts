import type { Zone } from '@/features/dashboard/types'

export interface CorredorGastronomico {
  id: string
  nombre: string
  saturacion: 'baja' | 'media' | 'alta'
  tipo: 'peñas' | 'comida_rapida' | 'parrillas' | 'food_trucks' | 'mixto'
  posibilidadSentarse: 'alta' | 'media' | 'baja'
  distancia: number
  x: number
  y: number
  referencia: string
  updatedAt: number
}

export interface ZonaEstacionamiento {
  id: string
  nombre: string
  distancia_min: number
  disponibilidad: number
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
  referencia: string
  lat: number
  lng: number
  updatedAt: number
}

export interface ZonaSalida {
  id: string
  nombre: string
  tipo: 'salida'
  transporte: 'auto' | 'transporte' | 'peatonal'
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
  distancia_min: number
  espera_min: number
  disponibilidad: number
  referencia: string
  lat: number
  lng: number
  capacidad_estimada?: number
  es_embudo?: boolean
  updatedAt: number
}

export interface PuntoSeguro {
  id: string
  nombre: string
  lat: number
  lng: number
  direccion: string
  referencia: string
  distancia_min: number
  horario: string
  telefono: string
  updatedAt: number
}

export interface PuestoSanitario {
  id: string
  nombre: string
  lat: number
  lng: number
  direccion: string
  referencia: string
  distancia_min: number
  horario: string
  telefono: string
  servicios: string[]
  updatedAt: number
}

export interface PuntoComida {
  id: string
  nombre: string
  tipo: 'comer'
  categoria: 'rapido' | 'comida' | 'bebida'
  distancia_min: number
  espera_min: number
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
  disponibilidad: number
  referencia: string
  lat: number
  lng: number
  geometryType: 'point' | 'line'
  coordinates: [number, number] | [number, number][]
  updatedAt: number
}

export interface PuntoPernoctar {
  id: string
  nombre: string
  tipo: 'pernoctar'
  categoria: 'hotel' | 'hostel' | 'camping' | 'hospedaje'
  distancia_min: number
  disponibilidad?: 'disponible' | 'consultar' | 'completo'
  telefono?: string
  web?: string
  referencia: string
  lat: number
  lng: number
  updatedAt: number
}

const satToDisp: Record<string, number> = { bajo: 90, medio: 55, alto: 30, colapsado: 8 }

export const mapZonesToParadas = (zones: Zone[]): CorredorGastronomico[] => {
  return zones
    .filter(z => z.type === 'comida')
    .map(z => ({
      id: z.id,
      nombre: z.name,
      saturacion: (z.saturation === 'bajo' ? 'baja' : z.saturation === 'medio' ? 'media' : 'alta') as 'baja' | 'media' | 'alta',
      tipo: (z.tipo_culinario || 'mixto') as CorredorGastronomico['tipo'],
      posibilidadSentarse: (z.posibilidadSentarse || 'media') as 'alta' | 'media' | 'baja',
      distancia: z.distancia_min || 5,
      x: z.x || 50,
      y: z.y || 50,
      referencia: z.referencia || z.name || '',
      updatedAt: Date.now()
    }))
}

export const mapZonesToEstacionamiento = (zones: Zone[]): ZonaEstacionamiento[] => {
  return zones
    .filter(z => z.type === 'estacionamiento')
    .map(z => ({
      id: z.id,
      nombre: z.name,
      distancia_min: z.distancia_min || 5,
      disponibilidad: satToDisp[z.saturation] ?? 50,
      estado: z.saturation,
      referencia: z.referencia || z.name || '',
      lat: z.lat || 0,
      lng: z.lng || 0,
      updatedAt: Date.now()
    }))
}

export const mapZonesToSalidas = (zones: Zone[]): ZonaSalida[] => {
  return zones
    .filter(z => z.type === 'salida')
    .map(z => ({
      id: z.id,
      nombre: z.name,
      tipo: 'salida' as const,
      transporte: (z.transporte || 'peatonal') as ZonaSalida['transporte'],
      estado: z.saturation,
      distancia_min: z.distancia_min || 5,
      espera_min: z.espera_min || 5,
      disponibilidad: satToDisp[z.saturation] ?? 50,
      referencia: z.referencia || z.name || '',
      lat: z.lat || 0,
      lng: z.lng || 0,
      capacidad_estimada: z.capacidad_estimada,
      es_embudo: z.es_embudo,
      updatedAt: Date.now()
    }))
}

const parseCoords = (raw: unknown): [number, number] | [number, number][] => {
  if (Array.isArray(raw)) {
    if (raw.length === 2 && typeof raw[0] === 'number' && typeof raw[1] === 'number') {
      return raw as [number, number]
    }
    if (raw.length > 0 && Array.isArray(raw[0])) {
      return raw as [number, number][]
    }
  }
  return [0, 0]
}

export const mapZonesToComida = (zones: Zone[]): PuntoComida[] => {
  return zones
    .filter(z => z.type === 'comida')
    .map(z => {
      // Priorizar lat/lng directo (como todos los demás mappers),
      // con fallback a coordinates si lat/lng no están disponibles
      let lat: number = z.lat ?? 0
      let lng: number = z.lng ?? 0

      if (!lat && !lng && z.coordinates) {
        const coords = parseCoords(z.coordinates)
        const isLine = z.geometry_type === 'line' && Array.isArray(coords[0])
        lat = isLine ? (coords as [number, number][])[0][0] : (coords as [number, number])[0]
        lng = isLine ? (coords as [number, number][])[0][1] : (coords as [number, number])[1]
      }

      const coords = parseCoords(z.coordinates)

      return {
        id: z.id,
        nombre: z.name,
        tipo: 'comer' as const,
        categoria: (z.subtipo === 'rapido' ? 'rapido' : z.subtipo === 'bebida' ? 'bebida' : 'comida') as PuntoComida['categoria'],
        distancia_min: z.distancia_min || 5,
        espera_min: z.espera_min || 5,
        estado: z.saturation,
        disponibilidad: satToDisp[z.saturation] ?? 50,
        referencia: z.referencia || z.name || '',
        lat,
        lng,
        geometryType: (z.geometry_type === 'line' ? 'line' : 'point') as 'point' | 'line',
        coordinates: coords,
        updatedAt: Date.now()
      }
    })
}

export const mapZonesToPernoctar = (zones: Zone[]): PuntoPernoctar[] => {
  return zones
    .filter(z => z.type === 'hospedaje')
    .map(z => ({
      id: z.id || '',
      nombre: z.name || '',
      tipo: 'pernoctar' as const,
      categoria: (z.subtipo as PuntoPernoctar['categoria']) ?? 'hospedaje',
      distancia_min: z.distancia_min || 5,
      disponibilidad: (z.saturation === 'bajo' ? 'disponible' : z.saturation === 'medio' ? 'consultar' : 'completo') as PuntoPernoctar['disponibilidad'],
      telefono: z.telefono || '',
      web: z.web || '',
      referencia: z.referencia || z.name || '',
      lat: z.lat || 0,
      lng: z.lng || 0,
      updatedAt: Date.now()
    }))
}

export const mapZonesToEmergencia = (zones: Zone[]): { puntoSeguro: PuntoSeguro; puestoSanitario: PuestoSanitario; zonasReferencia: { nombre: string; salidaCercana: string; distanciaSalida: number; zonaTranquila: string; distanciaTranquila: number } } => {
  const emergenciaZones = zones.filter(z => z.type === 'emergencia')
  const first = emergenciaZones[0]

  return {
    puntoSeguro: {
      id: first?.id || 'punto-default',
      nombre: first?.name || 'Punto de Referencia',
      lat: first?.lat || 0,
      lng: first?.lng || 0,
      direccion: first?.direccion || '',
      referencia: first?.referencia || first?.name || '',
      distancia_min: first?.distancia_min || 5,
      horario: first?.horario || '24hs',
      telefono: first?.telefono || '',
      updatedAt: Date.now()
    },
    puestoSanitario: {
      id: 'puesto-' + (first?.id || 'default'),
      nombre: first?.name ? `Puesto ${first.name}` : 'Puesto Sanitario',
      lat: first?.lat || 0,
      lng: first?.lng || 0,
      direccion: first?.direccion || '',
      referencia: first?.referencia || first?.name || '',
      distancia_min: first?.distancia_min || 5,
      horario: first?.horario || '24hs',
      telefono: first?.telefono || '',
      servicios: first?.servicios || ['Primeros auxilios'],
      updatedAt: Date.now()
    },
    zonasReferencia: {
      nombre: first?.name || 'Zona Centro',
      salidaCercana: 'Av. Principal',
      distanciaSalida: first?.distancia_min || 3,
      zonaTranquila: first?.referencia || 'Plaza Principal',
      distanciaTranquila: first?.distancia_min ? first.distancia_min + 2 : 5
    }
  }
}
