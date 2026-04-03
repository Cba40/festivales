import { zonasSalida, ZonaSalida, getSalidasOrdenadas } from './mockSalidas'
import { mockZones, Zona, getZonasOrdenadas } from './mockZones'

export type TipoInferencia = 'estacionar' | 'salir' | 'emergencia' | 'fallback'
export type ModoRespuesta = 'guiar' | 'asistir' | 'informar'

export interface ResultadoInferencia {
  tipo: TipoInferencia
  modo: ModoRespuesta
  mensaje: string
  zonaPrincipal?: ZonaSalida | Zona
  zonaAlternativa?: ZonaSalida | Zona
  confianza: 'alta' | 'media' | 'baja'
  contexto: {
    hora: string
    zona: string
    saturacion: 'baja' | 'media' | 'alta' | 'colapsada'
  }
}

const getZonaConMejorScore = (): Zona | undefined => {
  const ordenadas = getZonasOrdenadas()
  return ordenadas.find(z => z.estado !== 'colapsado')
}

const getZonaAlternativa = (): Zona | undefined => {
  const ordenadas = getZonasOrdenadas().filter(z => z.estado !== 'colapsado')
  return ordenadas[1]
}

const getSalidaConMenorCongestion = (): ZonaSalida | undefined => {
  const ordenadas = getSalidasOrdenadas(zonasSalida)
  return ordenadas.find(z => z.congestion !== 'colapsado')
}

const getSalidaAlternativa = (): ZonaSalida | undefined => {
  const ordenadas = getSalidasOrdenadas(zonasSalida).filter(z => z.congestion !== 'colapsado')
  return ordenadas[1]
}

const getZonaLejana = (): Zona | undefined => {
  const ordenadas = getZonasOrdenadas()
  return ordenadas[ordenadas.length - 1]
}

const getSaturacionActual = (): 'baja' | 'media' | 'alta' | 'colapsada' => {
  const zonaActual = mockZones.find(z => z.id === 'zona-actual')
  if (!zonaActual) return 'media'
  const map: Record<string, 'baja' | 'media' | 'alta' | 'colapsada'> = {
    bajo: 'baja',
    medio: 'media',
    alto: 'alta',
    colapsado: 'colapsada'
  }
  return map[zonaActual.estado] || 'media'
}

export const inferirNecesidad = (
  hora?: number,
  saturacion?: 'baja' | 'media' | 'alta' | 'colapsada',
  zonaActual?: string,
  ultimaAccion?: string
): ResultadoInferencia => {
  const h = hora ?? new Date().getHours()
  const sat = saturacion ?? getSaturacionActual()
  const zona = zonaActual ?? 'Zona Centro'

  // REGLA 1: LLEGADA (pre-evento) 18:00–21:00
  if (h >= 18 && h < 21) {
    return {
      tipo: 'estacionar',
      modo: 'guiar',
      mensaje: 'Horario de llegada → Estacioná ahora',
      zonaPrincipal: getZonaConMejorScore(),
      zonaAlternativa: getZonaAlternativa(),
      confianza: 'alta',
      contexto: { hora: `${h}:00`, zona, saturacion: sat }
    }
  }

  // REGLA 2: PICO / INGRESO 21:00–23:00
  if (h >= 21 && h <= 23) {
    return {
      tipo: 'estacionar',
      modo: 'guiar',
      mensaje: 'Horario pico → Zona alternativa',
      zonaPrincipal: getZonaConMejorScore(),
      zonaAlternativa: getZonaAlternativa(),
      confianza: 'alta',
      contexto: { hora: `${h}:00`, zona, saturacion: 'alta' }
    }
  }

  // REGLA 3: DENTRO DEL EVENTO 22:00–01:00
  if (h >= 22 || h <= 1) {
    return {
      tipo: 'salir',
      modo: 'asistir',
      mensaje: 'Prepará salida anticipada',
      zonaPrincipal: getSalidaConMenorCongestion(),
      zonaAlternativa: getSalidaAlternativa(),
      confianza: 'media',
      contexto: { hora: `${h}:00`, zona, saturacion: sat }
    }
  }

  // REGLA 4: SALIDA MASIVA 00:00–02:00
  if (h >= 0 && h <= 2) {
    return {
      tipo: 'salir',
      modo: 'guiar',
      mensaje: 'Salida masiva → Mejor ruta ahora',
      zonaPrincipal: getSalidaConMenorCongestion(),
      zonaAlternativa: getSalidaAlternativa(),
      confianza: 'alta',
      contexto: { hora: `${h}:00`, zona, saturacion: 'alta' }
    }
  }

  // REGLA 5: SIN OPCIÓN CERCANA (colapsado total)
  if (sat === 'colapsada') {
    return {
      tipo: 'salir',
      modo: 'guiar',
      mensaje: 'Zona colapsada → Zona lejana',
      zonaPrincipal: getZonaLejana(),
      zonaAlternativa: undefined,
      confianza: 'baja',
      contexto: { hora: `${h}:00`, zona, saturacion: 'colapsada' }
    }
  }

  // REGLA 6: USUARIO REPITE ACCIÓN
  if (ultimaAccion === 'estacionar') {
    return {
      tipo: 'estacionar',
      modo: 'asistir',
      mensaje: 'Continuar buscando estacionamiento',
      zonaPrincipal: getZonaConMejorScore(),
      zonaAlternativa: getZonaAlternativa(),
      confianza: 'media',
      contexto: { hora: `${h}:00`, zona, saturacion: sat }
    }
  }

  // REGLA 7: FALLBACK (ninguna regla aplica)
  return {
    tipo: 'fallback',
    modo: 'informar',
    mensaje: '¿Qué necesitás ahora?',
    confianza: 'baja',
    contexto: { hora: `${h}:00`, zona, saturacion: sat }
  }
}
