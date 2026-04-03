export interface ZonaSalida {
  id: string
  nombre: string
  tipo: 'auto' | 'transporte' | 'peatonal'
  lat: number
  lng: number
  referencia: string
  distancia_min: number
  congestion: 'baja' | 'media' | 'alta' | 'colapsado'
  capacidad_estimada?: number
  espera_estimada_min?: number
  es_embudo?: boolean
  timestamp: string
  updatedAt: number
}

const CONGESTION_PENALIZATION = {
  baja: 1,
  media: 2,
  alta: 4,
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
    congestion: 'media',
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
    congestion: 'baja',
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
    congestion: 'baja',
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
    congestion: 'alta',
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
    congestion: 'colapsado',
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
  const congestionPenalty = CONGESTION_PENALIZATION[zona.congestion]

  // AJUSTE POR TIPO (cambia el resultado según modo)
  if (tipo === 'auto') {
    // Auto: evitar calles colapsadas, penalización extra
    if (zona.congestion === 'alta' || zona.congestion === 'colapsado') {
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
  // FILTRAR por tipo con compatibilidad cruzada
  const filtradas = zonas.filter(z => {
    if (tipo === 'auto') return z.tipo === 'auto' || z.tipo === 'peatonal'
    if (tipo === 'transporte') return z.tipo === 'transporte' || z.tipo === 'peatonal'
    if (tipo === 'peatonal') return z.tipo === 'peatonal' || z.tipo === 'auto'
    return true
  })

  // CALCULAR score con tipo
  const conScore = filtradas.map(z => ({
    ...z,
    _score: calcularScoreSalida(z, tipo)
  }))

  // SEPARAR colapsadas
  const colapsadas = conScore.filter(z => z.congestion === 'colapsado')
  const disponibles = conScore.filter(z => z.congestion !== 'colapsado')

  // ORDENAR por score y devolver sin el campo interno
  const ordenar = (arr: typeof conScore) =>
    arr.sort((a, b) => a._score - b._score).map(({ _score, ...rest }) => rest)

  return [
    ...ordenar(disponibles),
    ...ordenar(colapsadas)
  ]
}
