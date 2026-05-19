/**
 * Mock data para corredores/zonas gastronómicas
 * Estructura preparada para futura integración con BD
 * 
 * x, y: valores 0-100 (escala relativa del evento)
 * saturacion: nivel de ocupación territorial
 * posibilidadSentarse: probabilidad de encontrar lugar
 */

export interface CorredorGastronomico {
  id: string
  nombre: string
  saturacion: 'baja' | 'media' | 'alta'  // 🟢 🟡 🔴
  tipo: 'peñas' | 'comida_rapida' | 'parrillas' | 'food_trucks' | 'mixto'
  posibilidadSentarse: 'alta' | 'media' | 'baja'
  distancia: number  // minutos caminando
  x: number          // 0-100 posición horizontal
  y: number          // 0-100 posición vertical
  referencia: string
  updatedAt: number
}

const now = Date.now()

export const corredoresGastronicosMock: CorredorGastronomico[] = [
  // ===== BAJA SATURACIÓN =====
  {
    id: 'corredor-norte',
    nombre: 'Corredor Gastronómico Norte',
    saturacion: 'baja',
    tipo: 'comida_rapida',
    posibilidadSentarse: 'alta',
    distancia: 3,
    x: 25,
    y: 20,
    referencia: 'Food trucks y puestos rápidos',
    updatedAt: now - 2 * 60000
  },

  // ===== MEDIA SATURACIÓN =====
  {
    id: 'corredor-peñas',
    nombre: 'Zona Peñas Tradicionales',
    saturacion: 'media',
    tipo: 'peñas',
    posibilidadSentarse: 'media',
    distancia: 5,
    x: 60,
    y: 40,
    referencia: 'Peñas, bebidas y tapas',
    updatedAt: now - 3 * 60000
  },

  // ===== ALTA SATURACIÓN =====
  {
    id: 'corredor-central',
    nombre: 'Patio Gastronómico Central',
    saturacion: 'alta',
    tipo: 'parrillas',
    posibilidadSentarse: 'baja',
    distancia: 2,
    x: 50,
    y: 60,
    referencia: 'Parrillas, asados, comida al fuego',
    updatedAt: now - 1 * 60000
  },

  // ===== ADICIONALES (para mapa expandido) =====
  {
    id: 'corredor-oeste',
    nombre: 'Corredor Oeste - Food Trucks',
    saturacion: 'baja',
    tipo: 'food_trucks',
    posibilidadSentarse: 'alta',
    distancia: 7,
    x: 15,
    y: 70,
    referencia: 'Comida internacional, fusion',
    updatedAt: now - 4 * 60000
  },

  {
    id: 'corredor-lateral',
    nombre: 'Zona Lateral Mixta',
    saturacion: 'media',
    tipo: 'mixto',
    posibilidadSentarse: 'media',
    distancia: 6,
    x: 75,
    y: 50,
    referencia: 'Variedad de opciones',
    updatedAt: now - 5 * 60000
  }
]

export const getCorredoresOrdenados = (): CorredorGastronomico[] => {
  // Ordenar por: baja → media → alta saturación, luego por distancia
  const orden = { baja: 0, media: 1, alta: 2 }
  return [...corredoresGastronicosMock].sort((a, b) => {
    const satDiff = orden[a.saturacion] - orden[b.saturacion]
    return satDiff !== 0 ? satDiff : a.distancia - b.distancia
  })
}

export const getCorredoresPorSaturacion = (saturacion: 'baja' | 'media' | 'alta'): CorredorGastronomico[] => {
  return corredoresGastronicosMock
    .filter(c => c.saturacion === saturacion)
    .sort((a, b) => a.distancia - b.distancia)
}

export const getCorredorPorId = (id: string): CorredorGastronomico | null => {
  return corredoresGastronicosMock.find(c => c.id === id) || null
}

export const getTipoLabel = (tipo: string): string => {
  switch (tipo) {
    case 'peñas': return 'Peñas'
    case 'comida_rapida': return 'Comida Rápida'
    case 'parrillas': return 'Parrillas'
    case 'food_trucks': return 'Food Trucks'
    case 'mixto': return 'Mixto'
    default: return tipo
  }
}

export const getSentarseLabel = (posibilidad: string): string => {
  switch (posibilidad) {
    case 'alta': return '🟢 Fácil encontrar lugar'
    case 'media': return '🟡 Moderadamente disponible'
    case 'baja': return '🔴 Muy concurrido'
    default: return posibilidad
  }
}
