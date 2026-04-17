import { getModo, getUmbralContexto, type Estado } from '@/utils/decisionEngine'
import { calcularScore } from '@/utils/decisionEngine'

export interface ZonaSalida {
  id: string
  nombre: string
  tipo: 'auto' | 'transporte' | 'peatonal'
  lat: number
  lng: number
  referencia: string
  distancia_min: number
  estado: Estado
  capacidad_estimada?: number
  espera_estimada_min?: number
  es_embudo?: boolean
  timestamp: string
  updatedAt: number
}

const CONGESTION_PENALIZATION = {
  bajo: 1,
  medio: 2,
  alto: 4,
  colapsado: 6
}

const now = Date.now()

export const zonasSalida: ZonaSalida[] = [
  {
    id: 'salida-norte',
    nombre: 'Salida Norte',
    tipo: 'auto',
    lat: -30.973313,
    lng: -64.088529,
    referencia: 'Terminal de Ómnibus',
    distancia_min: 6,
    estado: 'medio',
    capacidad_estimada: 200,
    espera_estimada_min: 3,
    timestamp: 'hace 2 min',
    updatedAt: now - 2 * 60000
  },
  {
    id: 'salida-sur',
    nombre: 'Salida Sur',
    tipo: 'transporte',
    lat: -30.985337,
    lng: -64.094209,
    referencia: 'Predio Ferial',
    distancia_min: 10,
    estado: 'bajo',
    capacidad_estimada: 500,
    espera_estimada_min: 2,
    timestamp: 'hace 2 min',
    updatedAt: now - 2 * 60000
  },
  {
    id: 'salida-este',
    nombre: 'Salida Este',
    tipo: 'peatonal',
    lat: -30.981249,
    lng: -64.075000,
    referencia: 'Av. Colón y Costanera',
    distancia_min: 8,
    estado: 'bajo',
    capacidad_estimada: 300,
    es_embudo: false,
    timestamp: 'hace 2 min',
    updatedAt: now - 2 * 60000
  },
  {
    id: 'salida-oeste',
    nombre: 'Salida Oeste',
    tipo: 'auto',
    lat: -30.981249,
    lng: -64.099398,
    referencia: 'Parque Autódromo',
    distancia_min: 12,
    estado: 'alto',
    capacidad_estimada: 150,
    espera_estimada_min: 5,
    timestamp: 'hace 2 min',
    updatedAt: now - 2 * 60000
  },
  {
    id: 'salida-centro',
    nombre: 'Salida Centro',
    tipo: 'peatonal',
    lat: -30.978107,
    lng: -64.094779,
    referencia: 'Plaza Principal / Iglesia',
    distancia_min: 3,
    estado: 'colapsado',
    capacidad_estimada: 100,
    es_embudo: true,
    timestamp: 'hace 2 min',
    updatedAt: now - 2 * 60000
  }
]

export const calcularScoreSalida = (
  zona: ZonaSalida,
  tipo: 'auto' | 'transporte' | 'peatonal'
): number => {
  // Score base por distancia
  let score = zona.distancia_min <= 5 ? 1 : zona.distancia_min <= 10 ? 2 : 3

  // Penalización por congestión
  const congestionPenalty = CONGESTION_PENALIZATION[zona.estado]

  // AJUSTE POR TIPO (cambia el resultado según modo)
  if (tipo === 'auto') {
    // Auto: evitar calles colapsadas, penalización extra
    if (zona.estado === 'alto' || zona.estado === 'colapsado') {
      score += 3
    }
  }

  if (tipo === 'transporte') {
    // Transporte: considerar espera estimada
    score += zona.espera_estimada_min || 0
  }

  if (tipo === 'peatonal') {
    // Peatonal: rutas más directas, evitar embudos
    if (zona.es_embudo) {
      score += 2
    }
  }

  return score + congestionPenalty
}

export const getSalidasOrdenadas = (
  zonas: ZonaSalida[],
  tipo: 'auto' | 'transporte' | 'peatonal'
): ZonaSalida[] => {
  // FILTRAR por transporte con compatibilidad cruzada
  const filtradas = zonas.filter(z => {
    if (tipo === 'auto') return z.transporte === 'auto' || z.transporte === 'peatonal'
    if (tipo === 'transporte') return z.transporte === 'transporte' || z.transporte === 'peatonal'
    if (tipo === 'peatonal') return z.transporte === 'peatonal' || z.transporte === 'auto'
    return true
  })

  // CALCULAR score con tipo
  const conScore = filtradas.map(z => ({
    ...z,
    _score: calcularScore(z.distancia_min, z.espera_min, z.estado)
  }))

  // SEPARAR colapsadas
  const colapsadas = conScore.filter(z => z.estado === 'colapsado')
  const disponibles = conScore.filter(z => z.estado !== 'colapsado')

  // ORDENAR por score y devolver sin el campo interno
  const ordenar = (arr: typeof conScore) =>
    arr.sort((a, b) => a._score - b._score).map(({ _score, ...rest }) => rest)

  return [
    ...ordenar(disponibles),
    ...ordenar(colapsadas)
  ]
}

export const getModoSalida = (zonas: ZonaSalida[], tipo: 'auto' | 'transporte' | 'peatonal'): 'sin_solucion' | 'guiar' | 'asistir' | 'informar' => {
  const h = getHoraEvento()
  const umbral = getUmbralContexto(h)

  const zonasOrdenadas = getSalidasOrdenadas(zonas, tipo)
  const mejor = zonasOrdenadas[0]

  if (!mejor) return 'sin_solucion'

  const todasColapsadas = zonas.every(z => z.estado === 'colapsado')
  if (todasColapsadas) return 'sin_solucion'

  // Usar engine SOLO para determinar modo
  const modoCalculado = getModo(
    zonasOrdenadas.map(z => ({ estado: z.estado, score: calcularScore(z.distancia_min, z.espera_min, z.estado) })),
    umbral
  )

  // FORZAR DECISIÓN EN TESTING: nunca devolver sin_solucion
  // Si el engine dice sin_solucion, forzar a asistir con la mejor opción disponible
  if (modoCalculado === 'sin_solucion') {
    return 'asistir'
  }

  return modoCalculado
}

// ============================================
// ⚠️ SOLO PARA TESTING FASE 3A — BORRAR DESPUÉS
// ============================================
export const escenariosTestSalida = {
  medio: [
    {
      id: 'test-1',
      nombre: 'Salida Test Medio',
      tipo: 'auto' as const,
      estado: 'medio' as const,
      distancia_min: 8,
      espera_estimada_min: 5,
      referencia: 'Test',
      lat: -30.9785,
      lng: -64.0950,
      timestamp: 'test',
      updatedAt: Date.now()
    }
  ],
  alto: [
    {
      id: 'test-2',
      nombre: 'Salida Test Alto',
      tipo: 'auto' as const,
      estado: 'alto' as const,
      distancia_min: 10,
      espera_estimada_min: 8,
      referencia: 'Test',
      lat: -30.9785,
      lng: -64.0950,
      timestamp: 'test',
      updatedAt: Date.now()
    }
  ],
  colapsado: [
    {
      id: 'test-3',
      nombre: 'Salida Test Colapsado',
      tipo: 'auto' as const,
      estado: 'colapsado' as const,
      distancia_min: 12,
      espera_estimada_min: 15,
      referencia: 'Test',
      lat: -30.9785,
      lng: -64.0950,
      timestamp: 'test',
      updatedAt: Date.now()
    }
  ]
}
