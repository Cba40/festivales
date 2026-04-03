// Tipos atómicos
export type EstadoZona = 'bajo' | 'medio' | 'alto' | 'colapsado'
export type Tendencia = 'subiendo' | 'estable' | 'bajando'
export type ModoRespuesta = 'informar' | 'asistir' | 'guiar'
export type TipoZona = 'estacionamiento' | 'transporte' | 'comida' | 'descanso' | 'servicios' | 'emergencia'

// Interface principal
export interface Zona {
  id: string
  nombre: string
  tipo: TipoZona
  distancia_min: number // en cuadras
  estado: EstadoZona
  capacidad_estimada: number
  tendencia: Tendencia
  timestamp: string // "actualizado hace X min"
  lat?: number // opcional para futuro mapa
  lng?: number
  referencia?: string
  updatedAt?: number
}

// Output de decisión
export interface Decision {
  zona_principal: Zona | null
  zona_fallback: Zona | null
  modo: ModoRespuesta
  confianza: 'alta' | 'media' | 'baja'
  mensaje_estado: string
  mensaje_accion: string
  mensaje_riesgo?: string
  mensaje_advertencia?: string
}

// Contexto del evento
export interface ContextoEvento {
  evento_id: string
  nombre: string
  fecha: string
  saturacion_general: EstadoZona
  hora_pico: boolean
}
