import { eventoData } from '@/data/eventoData'
import type { ZonaEstacionamiento, ZonaSalida } from './mappers'
import { mapZonesToEstacionamiento, mapZonesToSalidas } from './mappers'
import { getSalidasOrdenadas } from './mockSalidas'
import { getZonasOrdenadas } from './mockZones'
import { getHoraEvento } from '@/utils/contextoEvento'
import { getFaseActual } from '@/utils/fases'
import { getEventoConfig, fases } from '@/config/eventoConfig'

export type SaturacionTipo = 'baja' | 'media' | 'alta' | 'colapsada' | 'desconocida'

export interface SaturacionContexto {
  estacionamiento?: SaturacionTipo
  salida?: SaturacionTipo
}

export type TipoInferencia = 'estacionar' | 'salir' | 'emergencia' | 'fallback'
export type ModoRespuesta = 'guiar' | 'asistir' | 'informar'

export interface ResultadoInferencia {
  tipo: TipoInferencia
  modo: ModoRespuesta
  mensaje: string
  zonaPrincipal?: ZonaSalida | ZonaEstacionamiento
  zonaAlternativa?: ZonaSalida | ZonaEstacionamiento
  confianza: 'alta' | 'media' | 'baja'
  contexto: {
    hora: string
    zona: string
    saturacion: SaturacionTipo
  }
}

const getZonaConMejorScore = (zonas?: ZonaEstacionamiento[]) => {
  const data = zonas ?? eventoData.estacionamiento
  const ordenadas = getZonasOrdenadas(data)
  return ordenadas.find(z => z.estado !== 'colapsado')
}

const getZonaAlternativa = (zonas?: ZonaEstacionamiento[]) => {
  const data = zonas ?? eventoData.estacionamiento
  const ordenadas = getZonasOrdenadas(data).filter(z => z.estado !== 'colapsado')
  return ordenadas[1]
}

const getSalidaConMenorCongestion = (salidas?: ZonaSalida[]) => {
  const data = salidas ?? eventoData.salidas
  const ordenadas = getSalidasOrdenadas(data, 'auto')
  return ordenadas.find(z => z.estado !== 'colapsado')
}

const getSalidaAlternativa = (salidas?: ZonaSalida[]) => {
  const data = salidas ?? eventoData.salidas
  const ordenadas = getSalidasOrdenadas(data, 'auto').filter(z => z.estado !== 'colapsado')
  return ordenadas[1]
}

const getZonaLejana = (zonas?: ZonaEstacionamiento[]) => {
  const data = zonas ?? eventoData.estacionamiento
  const ordenadas = getZonasOrdenadas(data)
  return ordenadas[ordenadas.length - 1]
}

const esAccionValida = (accion: string, fase: { accion: string } | undefined) => {
  // 🔴 EMERGENCIA SIEMPRE VÁLIDA
  if (accion === 'emergencia') return true

  if (!fase) return true

  const compatibles: Record<string, string[]> = {
    estacionar: ['estacionar', 'salir'],
    salir: ['salir', 'estacionar'],
    emergencia: ['emergencia'],
    fallback: ['estacionar', 'salir', 'emergencia']
  }

  return compatibles[fase.accion]?.includes(accion)
}

export const inferirNecesidad = (
  hora?: number,
  saturacion?: SaturacionTipo | SaturacionContexto,
  zonaActual?: string,
  ultimaAccion?: string,
  zonasEstacionamiento?: ZonaEstacionamiento[],
  zonasSalida?: ZonaSalida[]
): ResultadoInferencia => {
  const h = hora ?? getHoraEvento()
  const zona = zonaActual ?? 'Zona Centro'
  const fase = getFaseActual(h)
  const config = getEventoConfig()

  // GUARDA DEFENSIVA: config.fases puede no existir
  const fasesDisponibles = config.fases ?? fases
  if (!fasesDisponibles || fasesDisponibles.length === 0) {
    console.warn('Evento sin configuración de fases')
  }

  // Backward compatibility: string → objeto
  const sat: SaturacionContexto = typeof saturacion === 'string'
    ? { estacionamiento: saturacion, salida: saturacion }
    : (saturacion ?? {})

  // Saturación según tipo de acción
  const saturacionActual: SaturacionTipo | undefined =
    fase?.accion === 'estacionar'
      ? sat.estacionamiento
      : fase?.accion === 'salir'
      ? sat.salida
      : undefined

  // Acción base: usuario tiene prioridad si es coherente con la fase
  const accionBase =
    (ultimaAccion && esAccionValida(ultimaAccion, fase))
      ? ultimaAccion
      : (fase?.accion === 'ninguna' ? 'fallback' : fase?.accion)

  // 1. COLAPSADO: mantener acción, ajustar modo y mensaje
  if (saturacionActual === 'colapsada') {
    if (accionBase === 'estacionar') {
      return {
        tipo: 'estacionar',
        modo: 'guiar',
        mensaje: 'Zona colapsada → Ir a zona lejana',
        zonaPrincipal: getZonaLejana(zonasEstacionamiento),
        zonaAlternativa: undefined,
        confianza: 'media',
        contexto: { hora: `${h}:00`, zona, saturacion: 'colapsada' }
      }
    }

    if (accionBase === 'salir') {
      return {
        tipo: 'salir',
        modo: 'guiar',
        mensaje: 'Zona colapsada → Salí ahora',
        zonaPrincipal: getSalidaConMenorCongestion(zonasSalida),
        zonaAlternativa: getSalidaAlternativa(zonasSalida),
        confianza: 'alta',
        contexto: { hora: `${h}:00`, zona, saturacion: 'colapsada' }
      }
    }
  }

  // 2. HAY FASE: usar configuración
  if (fase) {
    let modoFinal = fase.modo

    // 🔴 EMERGENCIA SIEMPRE GUIAR
    if (accionBase === 'emergencia') {
      modoFinal = 'guiar'
    }
    // ⚠️ ACCIÓN VÁLIDA PERO NO ÓPTIMA → ASISTIR
    else if (fase && accionBase !== fase.accion) {
      modoFinal = 'asistir'
    }

    return {
      tipo: accionBase ?? fase.accion,
      modo: modoFinal,
      mensaje: accionBase === 'estacionar'
        ? 'Buscá estacionamiento ahora'
        : accionBase === 'salir'
        ? 'Prepará salida anticipada'
        : '¿Qué necesitás ahora?',
      zonaPrincipal: accionBase === 'estacionar'
        ? getZonaConMejorScore(zonasEstacionamiento)
        : accionBase === 'salir'
        ? getSalidaConMenorCongestion(zonasSalida)
        : undefined,
      zonaAlternativa: accionBase === 'estacionar'
        ? getZonaAlternativa(zonasEstacionamiento)
        : accionBase === 'salir'
        ? getSalidaAlternativa(zonasSalida)
        : undefined,
      confianza: modoFinal === 'guiar' ? 'alta' : 'media',
      contexto: { hora: `${h}:00`, zona, saturacion: sat.estacionamiento ?? 'desconocida' }
    }
  }

  // 4. FALLBACK
  return {
    tipo: 'fallback',
    modo: 'informar',
    mensaje: '¿Qué necesitás ahora?',
    confianza: 'baja',
    contexto: { hora: `${h}:00`, zona, saturacion: 'desconocida' }
  }
}
