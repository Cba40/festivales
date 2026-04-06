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
  // ============================================
  // 🚗 ESTACIONAMIENTO (4 zonas con estados variados)
  // ============================================
  estacionamiento: [
    {
      id: 'est-norte',
      nombre: 'Estacionamiento Norte',
      tipo: 'estacionamiento' as const,
      distancia_min: 3,
      disponibilidad: 45,
      estado: 'medio' as const,
      referencia: 'Cerca de entrada principal',
      lat: -30.973313,
      lng: -64.088529,
      updatedAt: now - 2 * 60000
    },
    {
      id: 'est-sur',
      nombre: 'Estacionamiento Sur',
      tipo: 'estacionamiento' as const,
      distancia_min: 6,
      disponibilidad: 80,
      estado: 'bajo' as const,
      referencia: 'Zona secundaria',
      lat: -30.985337,
      lng: -64.094209,
      updatedAt: now - 1 * 60000
    },
    {
      id: 'est-vip',
      nombre: 'Estacionamiento VIP',
      tipo: 'estacionamiento' as const,
      distancia_min: 2,
      disponibilidad: 10,
      estado: 'alto' as const,
      referencia: 'Acceso exclusivo',
      lat: -30.978107,
      lng: -64.094779,
      updatedAt: now - 4 * 60000
    },
    {
      id: 'est-gral',
      nombre: 'Estacionamiento General',
      tipo: 'estacionamiento' as const,
      distancia_min: 5,
      disponibilidad: 0,
      estado: 'colapsado' as const,
      referencia: 'Área amplia - No usar',
      lat: -30.981249,
      lng: -64.099398,
      updatedAt: now - 10 * 60000
    }
  ] as ZonaEstacionamiento[],

  // ============================================
  // 🚌 TRANSPORTE (4 paradas con esperas variadas)
  // ============================================
  transporte: [
    {
      id: 'trans-a',
      nombre: 'Parada Línea A',
      tipo: 'transporte' as const,
      distancia_min: 2,
      estado: 'bajo' as const,
      espera_min: 8,
      referencia: 'Frente al escenario',
      calle: 'Av. Principal',
      lat: -30.973313,
      lng: -64.088529,
      updatedAt: now - 1 * 60000
    },
    {
      id: 'trans-b',
      nombre: 'Parada Línea B',
      tipo: 'transporte' as const,
      distancia_min: 4,
      estado: 'medio' as const,
      espera_min: 15,
      referencia: 'Salida lateral',
      calle: 'Calle Secundaria',
      lat: -30.978107,
      lng: -64.094779,
      updatedAt: now - 2 * 60000
    },
    {
      id: 'trans-c',
      nombre: 'Parada Express',
      tipo: 'transporte' as const,
      distancia_min: 3,
      estado: 'bajo' as const,
      espera_min: 5,
      referencia: 'Ruta directa',
      calle: 'Ruta Nacional',
      lat: -30.985337,
      lng: -64.094209,
      updatedAt: now - 1 * 60000
    },
    {
      id: 'trans-d',
      nombre: 'Parada Nocturna',
      tipo: 'transporte' as const,
      distancia_min: 7,
      estado: 'alto' as const,
      espera_min: 25,
      referencia: 'Solo después de 22hs',
      calle: 'Av. Nocturna',
      lat: -30.981249,
      lng: -64.099398,
      updatedAt: now - 3 * 60000
    }
  ] as ParadaTransporte[],

  // ============================================
  // 🍽 COMER (5 puntos con categorías mixtas)
  // ============================================
  comer: [
    {
      id: 'comer-1',
      nombre: 'Food Truck Central',
      tipo: 'comer' as const,
      categoria: 'rapido' as const,
      distancia_min: 1,
      espera_min: 5,
      estado: 'medio' as const,
      referencia: 'Plaza principal',
      lat: -30.973313,
      lng: -64.088529,
      updatedAt: now - 2 * 60000
    },
    {
      id: 'comer-2',
      nombre: 'Parrilla Festival',
      tipo: 'comer' as const,
      categoria: 'comida' as const,
      distancia_min: 3,
      espera_min: 12,
      estado: 'alto' as const,
      referencia: 'Zona gastronómica',
      lat: -30.978107,
      lng: -64.094779,
      updatedAt: now - 1 * 60000
    },
    {
      id: 'comer-3',
      nombre: 'Bar Rápido',
      tipo: 'comer' as const,
      categoria: 'bebida' as const,
      distancia_min: 2,
      espera_min: 3,
      estado: 'bajo' as const,
      referencia: 'Cerca de baños',
      lat: -30.985337,
      lng: -64.094209,
      updatedAt: now - 3 * 60000
    },
    {
      id: 'comer-4',
      nombre: 'Puesto Vegano',
      tipo: 'comer' as const,
      categoria: 'comida' as const,
      distancia_min: 4,
      espera_min: 8,
      estado: 'medio' as const,
      referencia: 'Área verde',
      lat: -30.981249,
      lng: -64.099398,
      updatedAt: now - 2 * 60000
    },
    {
      id: 'comer-5',
      nombre: 'Kiosco Express',
      tipo: 'comer' as const,
      categoria: 'rapido' as const,
      distancia_min: 2,
      espera_min: 2,
      estado: 'bajo' as const,
      referencia: 'Entrada norte',
      lat: -30.975000,
      lng: -64.090000,
      updatedAt: now - 1 * 60000
    }
  ] as PuntoComida[],

  // ============================================
  // 🚪 SALIR (4 salidas con opciones variadas)
  // ============================================
  salidas: [
    {
      id: 'sal-principal',
      nombre: 'Salida Principal',
      tipo: 'salida' as const,
      transporte: 'auto' as const,
      estado: 'alto' as const,
      distancia_min: 4,
      espera_min: 12,
      referencia: 'Acceso masivo',
      lat: -30.973313,
      lng: -64.088529,
      capacidad_estimada: 400,
      updatedAt: now - 2 * 60000
    },
    {
      id: 'sal-lateral',
      nombre: 'Salida Lateral',
      tipo: 'salida' as const,
      transporte: 'peatonal' as const,
      estado: 'bajo' as const,
      distancia_min: 6,
      espera_min: 5,
      referencia: 'Menos gente',
      lat: -30.978107,
      lng: -64.094779,
      capacidad_estimada: 200,
      updatedAt: now - 1 * 60000
    },
    {
      id: 'sal-vip',
      nombre: 'Salida VIP',
      tipo: 'salida' as const,
      transporte: 'auto' as const,
      estado: 'bajo' as const,
      distancia_min: 3,
      espera_min: 2,
      referencia: 'Acceso restringido',
      lat: -30.985337,
      lng: -64.094209,
      capacidad_estimada: 100,
      updatedAt: now - 3 * 60000
    },
    {
      id: 'sal-emergencia',
      nombre: 'Salida de Emergencia',
      tipo: 'salida' as const,
      transporte: 'peatonal' as const,
      estado: 'medio' as const,
      distancia_min: 8,
      espera_min: 0,
      referencia: 'Solo emergencias',
      lat: -30.981249,
      lng: -64.099398,
      capacidad_estimada: 150,
      es_embudo: false,
      updatedAt: now - 1 * 60000
    }
  ] as ZonaSalida[],

  // ============================================
  // 🚻 SERVICIOS GENERALES (2 por subtipo)
  // ============================================
  servicios: [
    // Baños
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
      id: 'svc-b2',
      nombre: 'Baños Sur',
      tipo: 'servicio' as const,
      subtipo: 'banos' as const,
      lat: -30.985337,
      lng: -64.094209,
      referencia: 'Cerca de escenario',
      distancia_min: 5,
      updatedAt: now - 3 * 60000
    },
    // Hidratación
    {
      id: 'svc-h1',
      nombre: 'Punto de Agua Central',
      tipo: 'servicio' as const,
      subtipo: 'hidratacion' as const,
      lat: -30.973313,
      lng: -64.088529,
      referencia: 'Plaza principal',
      distancia_min: 1,
      updatedAt: now - 2 * 60000
    },
    {
      id: 'svc-h2',
      nombre: 'Fuente Lateral',
      tipo: 'servicio' as const,
      subtipo: 'hidratacion' as const,
      lat: -30.978107,
      lng: -64.094779,
      referencia: 'Zona gastronómica',
      distancia_min: 3,
      updatedAt: now - 4 * 60000
    },
    // Descanso
    {
      id: 'svc-d1',
      nombre: 'Zona Sombría',
      tipo: 'servicio' as const,
      subtipo: 'descanso' as const,
      lat: -30.981249,
      lng: -64.099398,
      referencia: 'Área verde con bancos',
      distancia_min: 4,
      updatedAt: now - 6 * 60000
    },
    {
      id: 'svc-d2',
      nombre: 'Plaza de Descanso',
      tipo: 'servicio' as const,
      subtipo: 'descanso' as const,
      lat: -30.975000,
      lng: -64.090000,
      referencia: 'Con sombra y mesas',
      distancia_min: 6,
      updatedAt: now - 8 * 60000
    },
    // Salud
    {
      id: 'svc-s1',
      nombre: 'Primeros Auxilios',
      tipo: 'servicio' as const,
      subtipo: 'salud' as const,
      lat: -30.978107,
      lng: -64.094779,
      referencia: 'Módulo médico',
      distancia_min: 3,
      updatedAt: now - 1 * 60000
    },
    {
      id: 'svc-s2',
      nombre: 'Punto de Ayuda',
      tipo: 'servicio' as const,
      subtipo: 'salud' as const,
      lat: -30.985337,
      lng: -64.094209,
      referencia: 'Asistencia básica',
      distancia_min: 7,
      updatedAt: now - 2 * 60000
    }
  ] as PuntoServicio[],

  // ============================================
  // 🛏 DORMIR (4 alojamientos variados)
  // ============================================
  pernoctar: [
    {
      id: 'dormir-1',
      nombre: 'Hotel Centro',
      tipo: 'pernoctar' as const,
      categoria: 'hotel' as const,
      distancia_min: 6,
      disponibilidad: 'consultar' as const,
      telefono: '+543514000001',
      lat: -30.975000,
      lng: -64.090000,
      referencia: 'A 6 min caminando',
      updatedAt: now - 30 * 60000
    },
    {
      id: 'dormir-2',
      nombre: 'Hostel Festival',
      tipo: 'pernoctar' as const,
      categoria: 'hostel' as const,
      distancia_min: 4,
      disponibilidad: 'disponible' as const,
      telefono: '+543514000002',
      lat: -30.972000,
      lng: -64.087000,
      referencia: 'Ambiente joven',
      updatedAt: now - 45 * 60000
    },
    {
      id: 'dormir-3',
      nombre: 'Camping Municipal',
      tipo: 'pernoctar' as const,
      categoria: 'camping' as const,
      distancia_min: 9,
      disponibilidad: 'disponible' as const,
      lat: -30.970000,
      lng: -64.085000,
      referencia: 'Zona verde, llevar carpa',
      updatedAt: now - 60 * 60000
    },
    {
      id: 'dormir-4',
      nombre: 'Hospedaje Familiar',
      tipo: 'pernoctar' as const,
      categoria: 'hospedaje' as const,
      distancia_min: 5,
      disponibilidad: 'completo' as const,
      telefono: '+543514000004',
      lat: -30.976000,
      lng: -64.091000,
      referencia: 'Tranquilo, ideal familias',
      updatedAt: now - 40 * 60000
    }
  ] as PuntoPernoctar[]
}
