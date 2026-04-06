export type Modo = 'sin_solucion' | 'guiar' | 'asistir' | 'informar'

type ExitSessionState = {
  modoActual: Modo
  rutaActual: string | null
  ultimoCambio: number
}

export const crearExitSession = (modoInicial: Modo): ExitSessionState => ({
  modoActual: modoInicial,
  rutaActual: null,
  ultimoCambio: Date.now()
})

export const puedeCambiarModo = (
  nuevoModo: Modo,
  estado: ExitSessionState
): boolean => {
  // misma decisión → no hacer nada
  if (nuevoModo === estado.modoActual) return false

  // cooldown 60s
  if (Date.now() - estado.ultimoCambio < 60_000) return false

  // sin_solucion siempre permitido (seguridad)
  if (nuevoModo === 'sin_solucion') return true

  return true
}

export const aplicarCambioModo = (
  nuevoModo: Modo,
  estado: ExitSessionState
): ExitSessionState => {
  return {
    ...estado,
    modoActual: nuevoModo,
    ultimoCambio: Date.now()
  }
}

export type { ExitSessionState }
