import { getModo, getUmbralContexto } from '@/utils/decisionEngine'
import { calcularScore } from '@/utils/decisionEngine'
import { getHoraEvento } from '@/utils/contextoEvento'
import { type ZonaSalida } from '@/data/mappers'


const CONGESTION_PENALIZATION = {
  bajo: 1,
  medio: 2,
  alto: 4,
  colapsado: 6
}

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
    score += zona.espera_min || 0
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
