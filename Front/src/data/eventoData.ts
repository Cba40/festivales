// ============================================
// SINGLE SOURCE OF TRUTH — DATOS UNIFICADOS
// FASE 3C: fuente real de datos
// ============================================

export interface PuntoBase {
  id: string
  nombre: string
  lat: number
  lng: number
  referencia: string
  distancia_min: number
  updatedAt: number
}

export interface ZonaEstacionamiento extends PuntoBase {
  tipo: 'estacionamiento'
  disponibilidad: number
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
}

export interface ParadaTransporte extends PuntoBase {
  tipo: 'transporte'
  espera_min: number
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
  calle: string
}

export interface PuntoComida extends PuntoBase {
  tipo: 'comer'
  espera_min: number
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
  categoria: 'rapido' | 'comida' | 'bebida'
}

export interface ZonaSalida extends PuntoBase {
  tipo: 'salida'
  transporte: 'auto' | 'transporte' | 'peatonal'
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
  espera_min: number
  capacidad_estimada?: number
  es_embudo?: boolean
}

export interface PuntoServicio extends PuntoBase {
  tipo: 'servicio'
  subtipo: 'banos' | 'hidratacion' | 'descanso' | 'salud'
}

export interface PuntoPernoctar extends PuntoBase {
  tipo: 'pernoctar'
  categoria: 'hotel' | 'hostel' | 'camping' | 'hospedaje'
  disponibilidad?: 'disponible' | 'consultar' | 'completo'
  telefono?: string
  web?: string
}

const now = Date.now()

export const eventoData = {
  estacionamiento: [
    {
      id: 'zona-norte',
      nombre: 'Zona Norte',
      tipo: 'estacionamiento' as const,
      distancia_min: 6,
      disponibilidad: 15,
      estado: 'alto' as const,
      referencia: 'Barrio Norte / Terminal',
      lat: -30.973313,
      lng: -64.088529,
      updatedAt: now - 3 * 60000
    },
    {
      id: 'zona-oeste',
      nombre: 'Zona Oeste',
      tipo: 'estacionamiento' as const,
      distancia_min: 8,
      disponibilidad: 45,
      estado: 'medio' as const,
      referencia: 'Parque Autódromo',
      lat: -30.981249,
      lng: -64.099398,
      updatedAt: now - 5 * 60000
    },
    {
      id: 'zona-sur',
      nombre: 'Zona Sur',
      tipo: 'estacionamiento' as const,
      distancia_min: 10,
      disponibilidad: 80,
      estado: 'bajo' as const,
      referencia: 'Predio Ferial / Costanera',
      lat: -30.985337,
      lng: -64.094209,
      updatedAt: now - 1 * 60000
    }
  ] as ZonaEstacionamiento[],

  transporte: [
    {
      id: '1',
      nombre: 'Terminal Principal',
      tipo: 'transporte' as const,
      distancia_min: 5,
      estado: 'alto' as const,
      espera_min: 20,
      referencia: 'Frente a la Plaza',
      calle: 'Av. San Martín',
      lat: -30.9785,
      lng: -64.0950,
      updatedAt: now - 2 * 60000
    },
    {
      id: '2',
      nombre: 'Parada Secundaria',
      tipo: 'transporte' as const,
      distancia_min: 8,
      estado: 'bajo' as const,
      espera_min: 10,
      referencia: 'Esquina Av. Colón',
      calle: 'Av. Colón',
      lat: -30.9810,
      lng: -64.0890,
      updatedAt: now - 1 * 60000
    },
    {
      id: '3',
      nombre: 'Parada Norte',
      tipo: 'transporte' as const,
      distancia_min: 12,
      estado: 'medio' as const,
      espera_min: 15,
      referencia: 'Terminal de Ómnibus',
      calle: 'Ruta 9',
      lat: -30.9733,
      lng: -64.0885,
      updatedAt: now - 3 * 60000
    }
  ] as ParadaTransporte[],

  comer: [
    {
      id: 'c1',
      nombre: 'Puesto Norte',
      tipo: 'comer' as const,
      categoria: 'rapido' as const,
      distancia_min: 6,
      espera_min: 10,
      estado: 'bajo' as const,
      referencia: 'Frente a la plaza secundaria',
      lat: -30.9733,
      lng: -64.0885,
      updatedAt: now - 2 * 60000
    },
    {
      id: 'c2',
      nombre: 'Zona Gastronómica Central',
      tipo: 'comer' as const,
      categoria: 'comida' as const,
      distancia_min: 3,
      espera_min: 25,
      estado: 'alto' as const,
      referencia: 'Predio principal',
      lat: -30.9781,
      lng: -64.0947,
      updatedAt: now - 1 * 60000
    },
    {
      id: 'c3',
      nombre: 'Puesto Oeste',
      tipo: 'comer' as const,
      categoria: 'rapido' as const,
      distancia_min: 8,
      espera_min: 12,
      estado: 'medio' as const,
      referencia: 'Parque Autódromo',
      lat: -30.9812,
      lng: -64.0993,
      updatedAt: now - 3 * 60000
    }
  ] as PuntoComida[],

  salidas: [
    {
      id: 'salida-norte',
      nombre: 'Salida Norte',
      tipo: 'salida' as const,
      transporte: 'auto' as const,
      estado: 'medio' as const,
      distancia_min: 6,
      espera_min: 3,
      referencia: 'Terminal de Ómnibus',
      lat: -30.973313,
      lng: -64.088529,
      capacidad_estimada: 200,
      updatedAt: now - 2 * 60000
    },
    {
      id: 'salida-sur',
      nombre: 'Salida Sur',
      tipo: 'salida' as const,
      transporte: 'transporte' as const,
      estado: 'bajo' as const,
      distancia_min: 10,
      espera_min: 2,
      referencia: 'Predio Ferial',
      lat: -30.985337,
      lng: -64.094209,
      capacidad_estimada: 500,
      updatedAt: now - 2 * 60000
    },
    {
      id: 'salida-este',
      nombre: 'Salida Este',
      tipo: 'salida' as const,
      transporte: 'peatonal' as const,
      estado: 'bajo' as const,
      distancia_min: 8,
      espera_min: 0,
      referencia: 'Av. Colón y Costanera',
      lat: -30.981249,
      lng: -64.075000,
      es_embudo: false,
      updatedAt: now - 2 * 60000
    },
    {
      id: 'salida-oeste',
      nombre: 'Salida Oeste',
      tipo: 'salida' as const,
      transporte: 'auto' as const,
      estado: 'alto' as const,
      distancia_min: 12,
      espera_min: 5,
      referencia: 'Parque Autódromo',
      lat: -30.981249,
      lng: -64.099398,
      capacidad_estimada: 150,
      updatedAt: now - 2 * 60000
    },
    {
      id: 'salida-centro',
      nombre: 'Salida Centro',
      tipo: 'salida' as const,
      transporte: 'peatonal' as const,
      estado: 'colapsado' as const,
      distancia_min: 3,
      espera_min: 0,
      referencia: 'Plaza Principal / Iglesia',
      lat: -30.978107,
      lng: -64.094779,
      capacidad_estimada: 100,
      es_embudo: true,
      updatedAt: now - 2 * 60000
    }
  ] as ZonaSalida[],

  servicios: [
    {
      id: 'svc-b1',
      nombre: 'Baños Norte',
      tipo: 'servicio' as const,
      subtipo: 'banos' as const,
      lat: -30.973313,
      lng: -64.088529,
      referencia: 'Junto a entrada principal',
      distancia_min: 2,
      updatedAt: now - 5 * 60000
    },
    {
      id: 'svc-h1',
      nombre: 'Punto de Agua Central',
      tipo: 'servicio' as const,
      subtipo: 'hidratacion' as const,
      lat: -30.978107,
      lng: -64.094779,
      referencia: 'Plaza central',
      distancia_min: 3,
      updatedAt: now - 3 * 60000
    },
    {
      id: 'svc-d1',
      nombre: 'Zona de Descanso Sombría',
      tipo: 'servicio' as const,
      subtipo: 'descanso' as const,
      lat: -30.981249,
      lng: -64.099398,
      referencia: 'Área verde con bancos',
      distancia_min: 4,
      updatedAt: now - 10 * 60000
    },
    {
      id: 'svc-s1',
      nombre: 'Puesto de Primeros Auxilios',
      tipo: 'servicio' as const,
      subtipo: 'salud' as const,
      lat: -30.980100,
      lng: -64.093500,
      referencia: 'Módulo médico',
      distancia_min: 3,
      updatedAt: now - 1 * 60000
    }
  ] as PuntoServicio[],

  pernoctar: [
    {
      id: 'p1',
      nombre: 'Hotel Central',
      tipo: 'pernoctar' as const,
      categoria: 'hotel' as const,
      distancia_min: 5,
      disponibilidad: 'consultar' as const,
      telefono: '+543510000001',
      lat: -30.9750,
      lng: -64.0900,
      referencia: 'Centro',
      updatedAt: now - 30 * 60000
    },
    {
      id: 'p2',
      nombre: 'Camping Municipal',
      tipo: 'pernoctar' as const,
      categoria: 'camping' as const,
      distancia_min: 8,
      disponibilidad: 'disponible' as const,
      lat: -30.9700,
      lng: -64.0850,
      referencia: 'Zona norte',
      updatedAt: now - 60 * 60000
    },
    {
      id: 'p3',
      nombre: 'Hostel Ruta 9',
      tipo: 'pernoctar' as const,
      categoria: 'hostel' as const,
      distancia_min: 6,
      disponibilidad: 'consultar' as const,
      telefono: '+543510000002',
      lat: -30.9720,
      lng: -64.0870,
      referencia: 'Ruta 9',
      updatedAt: now - 45 * 60000
    }
  ] as PuntoPernoctar[]
}
