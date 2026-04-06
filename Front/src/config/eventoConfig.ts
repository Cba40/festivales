export type ConfigEvento = {
  ventanas: {
    llegada: [number, number]
    pico: [number, number]
    dentro: [number, number]
    salida: [number, number]
  }
  estacionamiento: {
    colapsadoThreshold: number
    criticoThreshold: number
  }
}

export type TipoAccion = 'estacionar' | 'salir' | 'emergencia' | 'fallback'

export type FaseEvento = {
  id: string
  nombre: string
  rango: [number, number]
  accion: TipoAccion
  modo: 'guiar' | 'asistir' | 'informar'
  // TODO: soporte multi-día cuando exista fuente de día del evento
}

export const fases: FaseEvento[] = [
  {
    id: 'llegada',
    nombre: 'Llegada',
    rango: [18, 20],
    accion: 'estacionar',
    modo: 'guiar'
  },
  {
    id: 'pico',
    nombre: 'Pico de ingreso',
    rango: [21, 21],
    accion: 'estacionar',
    modo: 'guiar'
  },
  {
    id: 'dentro',
    nombre: 'Dentro del evento',
    rango: [22, 23],
    accion: 'salir',
    modo: 'asistir'
  },
  {
    id: 'salida',
    nombre: 'Salida masiva',
    rango: [0, 2],
    accion: 'salir',
    modo: 'guiar'
  }
]

export const eventoConfig: ConfigEvento = {
  ventanas: {
    llegada: [18, 20],
    pico: [21, 21],
    dentro: [22, 23],
    salida: [0, 2]
  },
  estacionamiento: {
    colapsadoThreshold: 10,
    criticoThreshold: 15
  }
}

export const getEventoConfig = () => eventoConfig
