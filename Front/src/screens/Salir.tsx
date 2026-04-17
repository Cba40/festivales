import { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Map, X } from 'lucide-react'
import {
  getSalidasOrdenadas,
  getModoSalida,
  calcularScoreSalida,
  ZonaSalida
} from '@/data/mockSalidas'
import { eventoData } from '@/data/eventoData'
import { getConfianza, getConfianzaLabel } from '@/utils/confianza'
import { formatUpdatedAt } from '@/utils/formatTime'
import {
  crearExitSession,
  puedeCambiarModo,
  aplicarCambioModo,
  type ExitSessionState
} from '@/utils/exitSessionController'

type TipoTransporte = 'auto' | 'transporte' | 'peatonal'

const Salir = () => {
  const navigate = useNavigate()
  const [tipo, setTipo] = useState<TipoTransporte>('auto')
  const [selectedZona, setSelectedZona] = useState<ZonaSalida | null>(null)

  // Usar datos de eventoData (single source of truth)
  const zonasMock = eventoData.salidas

  // Modo inicial desde engine
  const modoInicial = getModoSalida(zonasMock, tipo)
  const [session, setSession] = useState<ExitSessionState>(
    crearExitSession(modoInicial)
  )

  // Reset de sesión cuando cambia el escenario
  useEffect(() => {
    const modoInicial = getModoSalida(zonasMock, tipo)
    setSession(crearExitSession(modoInicial))
  }, [zonasMock])

  const salidasOrdenadas = useMemo(() => {
    return getSalidasOrdenadas(zonasMock, tipo)
  }, [zonasMock, tipo])

  const salidasModo = useMemo(() => {
    const filtradas = zonasMock.filter(salida => salida.transporte === tipo)
    if (filtradas.length > 0) {
      return getSalidasOrdenadas(filtradas, tipo)
    }
    return [salidasOrdenadas[0]].filter(Boolean) as ZonaSalida[]
  }, [zonasMock, tipo, salidasOrdenadas])

  const mensajeModo = salidasModo[0]?.transporte !== tipo
    ? 'No hay opciones rápidas en este modo'
    : ''

  const principal = salidasModo[0]
  const alternativaRaw = salidasModo[1]
  const esAlternativaValida = alternativaRaw &&
    calcularScoreSalida(alternativaRaw, tipo) <
    Math.min(
      calcularScoreSalida(principal, tipo) * 0.85,
      6
    )
  const alternativa = esAlternativaValida ? alternativaRaw : undefined

  // Actualizar modo con controller (cooldown + logging)
  useEffect(() => {
    const nuevoModo = getModoSalida(zonasMock, tipo)

    if (puedeCambiarModo(nuevoModo, session)) {
      console.log('modo_cambiado', {
        anterior: session.modoActual,
        nuevo: nuevoModo,
        timestamp: Date.now()
      })
      setSession(aplicarCambioModo(nuevoModo, session))
    } else {
      console.log('cambio_rechazado', {
        actual: session.modoActual,
        sugerido: nuevoModo,
        razon: nuevoModo === session.modoActual ? 'mismo_modo' : 'cooldown_activo'
      })
    }
  }, [tipo])

  // Logging de test
  useEffect(() => {
    console.log('=== 🧪 TEST SALIR ===')
    console.log('Zonas:', zonasMock.map(z => ({
      nombre: z.nombre,
      estado: z.estado,
      score: calcularScoreSalida(z, tipo)
    })))
    console.log('Modo final:', session.modoActual)
    console.log('======================')
  }, [session.modoActual, zonasMock, tipo])

  useEffect(() => {
    console.log('=== TEST MODOS ===')
    console.log('AUTO:', getSalidasOrdenadas(zonasMock, 'auto'))
    console.log('TRANSPORTE:', getSalidasOrdenadas(zonasMock, 'transporte'))
    console.log('PEATONAL:', getSalidasOrdenadas(zonasMock, 'peatonal'))
    console.log('===================')
  }, [zonasMock])

  const abrirMapa = (zona: ZonaSalida) => {
    if (zona.lat && zona.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${zona.lat},${zona.lng}`,
        '_blank'
      )
    }
    setSelectedZona(null)
  }

  const getEstadoStyles = (estado: string) => {
    switch (estado) {
      case 'bajo': return 'bg-success/20 text-success'
      case 'medio': return 'bg-warning/20 text-warning'
      case 'alto': return 'bg-danger/20 text-danger'
      case 'colapsado': return 'bg-gray-500/20 text-gray-500'
      default: return 'bg-gray-500/20 text-gray-500'
    }
  }

  const getEstadoLabel = (estado: string) => {
    switch (estado) {
      case 'bajo': return '🟢 Bajo'
      case 'medio': return '🟡 Medio'
      case 'alto': return '🔴 Alto'
      case 'colapsado': return '⚫ Colapsado'
      default: return estado
    }
  }

  const salirDescription = (
    <div className="text-xs text-gray-500 mb-2">
      Te mostramos la forma más rápida de salir según el flujo actual
    </div>
  )

  // SIN SOLUCIÓN
  if (session.modoActual === 'sin_solucion') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Salir" showBack onBack={() => navigate('/')} />      {salirDescription}
        <div className="flex-1 p-4 space-y-4">
          {/* Selector tipo */}
          <div className="grid grid-cols-3 gap-2">
            {(['auto', 'transporte', 'peatonal'] as TipoTransporte[]).map(t => (
              <button
                key={t}
                onClick={() => setTipo(t)}
                className={`p-3 rounded-xl font-bold transition-transform active:scale-95 ${
                  tipo === t ? 'bg-primary text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
                }`}
              >
                {t === 'auto' ? '🚗 Auto' : t === 'transporte' ? '🚌 Transporte' : '🚶 Caminando'}
              </button>
            ))}
          </div>
          {mensajeModo && (
            <div className="bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 text-yellow-900 dark:text-yellow-100 p-3 rounded-xl">
              {mensajeModo}
            </div>
          )}

          <div className="bg-warning/20 text-amber-900 border border-amber-300 dark:bg-amber-950/40 dark:border-amber-700 p-6 rounded-xl text-center">
            <p className="text-xl font-bold">⚠️ Todas las salidas con demora</p>
            <p className="text-sm mt-2 opacity-90">Te mostramos la mejor disponible</p>
          </div>

          {principal && (
            <button onClick={() => setSelectedZona(principal)} className="w-full">
              <div className="bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left shadow-sm">
                <p className="font-bold text-slate-800 dark:text-slate-100">Mejor opción disponible</p>
                <p className="text-lg font-bold mt-2">{principal.nombre}</p>
                <p className="text-sm text-slate-600 dark:text-slate-300 mt-2">📍 {principal.referencia}</p>
                <p className="text-sm text-slate-600 dark:text-slate-300">🚶 {principal.distancia_min} min · ⏱️ {principal.espera_min} min</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">{getEstadoLabel(principal.estado)}</p>
              </div>
            </button>
          )}

          <div className="bg-slate-100 dark:bg-slate-700 p-4 rounded-xl text-center text-slate-700 dark:text-slate-300">
            {mensajeModo || 'Ningún modo rápido disponible, pero puedes usar la opción mostrada.'}
          </div>

          {principal && (
            <button
              onClick={() => abrirMapa(principal)}
              className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg transition-transform active:scale-95 shadow-lg flex items-center justify-center gap-2"
            >
              <Map size={20} /> Iniciar ruta
            </button>
          )}
        </div>
      </div>
    )
  }

  // GUIAR
  if (session.modoActual === 'guiar') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Salir" showBack onBack={() => navigate('/')} />
      {salirDescription}

        <div className="bg-danger text-white px-4 py-3">
          <h2 className="font-bold text-lg">👉 Salidas congestionadas</h2>
        </div>

        <div className="flex-1 p-4 space-y-4">
          {/* Selector tipo */}
          <div className="grid grid-cols-3 gap-2">
            {(['auto', 'transporte', 'peatonal'] as TipoTransporte[]).map(t => (
              <button
                key={t}
                onClick={() => setTipo(t)}
                className={`p-3 rounded-xl font-bold transition-transform active:scale-95 ${
                  tipo === t ? 'bg-primary text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
                }`}
              >
                {t === 'auto' ? '🚗 Auto' : t === 'transporte' ? '🚌 Transporte' : '🚶 Caminando'}
              </button>
            ))}
          </div>

          {mensajeModo && (
            <div className="bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 text-yellow-900 dark:text-yellow-100 p-3 rounded-xl">
              {mensajeModo}
            </div>
          )}

          {principal && (
            <button onClick={() => setSelectedZona(principal)} className="w-full">
              <div className="bg-primary text-white p-6 rounded-xl text-left shadow-lg border border-primary">
                <p className="text-sm font-semibold mb-2">🔥 Mejor opción ahora</p>
                <p className="text-lg font-bold">👉 Dirigite ahora a {principal.nombre}</p>
                <p className="text-sm opacity-90 mt-2">📍 {principal.referencia}</p>
                <p className="text-sm opacity-90">🚶 {principal.distancia_min} min</p>
                <p className="text-xs opacity-90 mt-2">Menor tiempo total de salida</p>
                {principal.estado === 'alto' && (
                  <p className="text-xs opacity-75 mt-2">⚠️ Congestión alta</p>
                )}
              </div>
            </button>
          )}

          {alternativa && principal.estado !== 'colapsado' && (
            <button onClick={() => setSelectedZona(alternativa)} className="w-full">
              <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
                <p className="font-bold text-slate-800 dark:text-slate-100">
                  👉 Si está lleno → {alternativa.nombre}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                  📍 {alternativa.referencia}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🚶 {alternativa.distancia_min} min
                </p>
              </div>
            </button>
          )}

          <p className="text-xs text-slate-400 dark:text-slate-500 text-center">
            {getConfianzaLabel(getConfianza(principal?.estado || 'medio'))}
          </p>

          {principal && (
            <button
              onClick={() => abrirMapa(principal)}
              className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg transition-transform active:scale-95 shadow-lg flex items-center justify-center gap-2"
            >
              <Map size={20} />
              Iniciar ruta
            </button>
          )}
        </div>

        {/* Bottom Sheet */}
        {selectedZona && (
          <>
            <div className="fixed inset-0 bg-black/50 z-40" onClick={() => setSelectedZona(null)} />
            <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
              <div className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer" onClick={() => setSelectedZona(null)} />
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">{selectedZona.nombre}</h3>
              <div className="space-y-2 mb-4">
                <p className="text-sm text-slate-600 dark:text-slate-300">📍 {selectedZona.referencia}</p>
                <p className="text-sm text-slate-600 dark:text-slate-300">🚶 {selectedZona.distancia_min} min</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{formatUpdatedAt(selectedZona.updatedAt)}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{getConfianzaLabel(getConfianza(selectedZona.estado))}</p>
              </div>
              <button onClick={() => abrirMapa(selectedZona)} className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 flex items-center justify-center gap-2"><Map size={20} /> Iniciar ruta</button>
              <button onClick={() => setSelectedZona(null)} className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold flex items-center justify-center gap-2"><X size={16} /> Cerrar</button>
            </div>
          </>
        )}
      </div>
    )
  }

  // ASISTIR
  if (session.modoActual === 'asistir') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Salir" showBack onBack={() => navigate('/')} />
        {salirDescription}

        <div className="flex-1 p-4 space-y-4">
          {/* Selector tipo */}
          <div className="grid grid-cols-3 gap-2">
            {(['auto', 'transporte', 'peatonal'] as TipoTransporte[]).map(t => (
              <button
                key={t}
                onClick={() => setTipo(t)}
                className={`p-3 rounded-xl font-bold transition-transform active:scale-95 ${
                  tipo === t ? 'bg-primary text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
                }`}
              >
                {t === 'auto' ? '🚗 Auto' : t === 'transporte' ? '🚌 Transporte' : '🚶 Caminando'}
              </button>
            ))}
          </div>

          {mensajeModo && (
            <div className="bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 text-yellow-900 dark:text-yellow-100 p-3 rounded-xl">
              {mensajeModo}
            </div>
          )}

          {principal && (
            <button onClick={() => setSelectedZona(principal)} className="w-full">
              <div className="bg-white dark:bg-slate-800 border-l-4 border-primary p-4 rounded-xl text-left shadow-md ring-1 ring-primary/20">
                <p className="text-sm font-semibold mb-2">🔥 Mejor opción ahora</p>
                <p className="font-bold text-slate-800 dark:text-slate-100 text-lg">
                  👉 Mejor opción ahora: {principal.nombre}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300 mt-2">📍 {principal.referencia}</p>
                <p className="text-sm text-slate-600 dark:text-slate-300">🚶 {principal.distancia_min} min</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">Menor tiempo total de salida</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">{formatUpdatedAt(principal.updatedAt)}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{getConfianzaLabel(getConfianza(principal.estado))}</p>
              </div>
            </button>
          )}

          {alternativa && (
            <button onClick={() => setSelectedZona(alternativa)} className="w-full">
              <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
                <p className="font-bold text-slate-800 dark:text-slate-100">Alternativa: {alternativa.nombre}</p>
                <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">📍 {alternativa.referencia}</p>
                <p className="text-sm text-slate-600 dark:text-slate-300">🚶 {alternativa.distancia_min} min</p>
              </div>
            </button>
          )}

          {principal && (
            <button
              onClick={() => abrirMapa(principal)}
              className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2"
            >
              <Map size={20} /> Iniciar ruta
            </button>
          )}
        </div>

        {/* Bottom Sheet */}
        {selectedZona && (
          <>
            <div className="fixed inset-0 bg-black/50 z-40" onClick={() => setSelectedZona(null)} />
            <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
              <div className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer" onClick={() => setSelectedZona(null)} />
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">{selectedZona.nombre}</h3>
              <div className="space-y-2 mb-4">
                <p className="text-sm text-slate-600 dark:text-slate-300">📍 {selectedZona.referencia}</p>
                <p className="text-sm text-slate-600 dark:text-slate-300">🚶 {selectedZona.distancia_min} min</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{formatUpdatedAt(selectedZona.updatedAt)}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{getConfianzaLabel(getConfianza(selectedZona.estado))}</p>
              </div>
              <button onClick={() => abrirMapa(selectedZona)} className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 flex items-center justify-center gap-2"><Map size={20} /> Iniciar ruta</button>
              <button onClick={() => setSelectedZona(null)} className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold flex items-center justify-center gap-2"><X size={16} /> Cerrar</button>
            </div>
          </>
        )}
      </div>
    )
  }

  // INFORMAR
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Salir" showBack onBack={() => navigate('/')} />
      {salirDescription}

      <div className="flex-1 p-4 space-y-4">
        {/* Selector tipo */}
        <div className="grid grid-cols-3 gap-2">
          {(['auto', 'transporte', 'peatonal'] as TipoTransporte[]).map(t => (
            <button
              key={t}
              onClick={() => setTipo(t)}
              className={`p-3 rounded-xl font-bold transition-transform active:scale-95 ${
                tipo === t ? 'bg-primary text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
              }`}
            >
              {t === 'auto' ? '🚗 Auto' : t === 'transporte' ? '🚌 Transporte' : '🚶 Caminando'}
            </button>
          ))}
        </div>

        {mensajeModo && (
          <div className="bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 text-yellow-900 dark:text-yellow-100 p-3 rounded-xl">
            {mensajeModo}
          </div>
        )}

        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-md">
          <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4">
            Salidas disponibles
          </h2>
          <div className="text-xs text-gray-500 mt-2 mb-4">
            🟢 Bajo: rápido · 🟡 Medio: demora moderada · 🔴 Alto: mucha demora
          </div>
          <div className="space-y-3">
            {salidasModo.slice(0, 3).map(zona => (
              <button key={zona.id} onClick={() => setSelectedZona(zona)}
                className="w-full p-4 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-left hover:border-primary transition-colors">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-gray-900 dark:text-gray-100">{zona.nombre}</span>
                  <span className={`px-2 py-1 rounded text-xs font-bold ${getEstadoStyles(zona.estado)}`}>{getEstadoLabel(zona.estado)}</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">📍 {zona.referencia}</p>
                <p className="text-sm text-gray-600 dark:text-gray-300">🚶 {zona.distancia_min} min</p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{formatUpdatedAt(zona.updatedAt)}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{getConfianzaLabel(getConfianza(zona.estado))}</p>
              </button>
            ))}
          </div>
        </div>

        {principal && (
          <button onClick={() => abrirMapa(principal)}
            className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2">
            <Map size={20} /> Iniciar ruta
          </button>
        )}
      </div>

      {/* Bottom Sheet */}
      {selectedZona && (
        <>
          <div className="fixed inset-0 bg-black/50 z-40" onClick={() => setSelectedZona(null)} />
          <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
            <div className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer" onClick={() => setSelectedZona(null)} />
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">{selectedZona.nombre}</h3>
            <div className="space-y-2 mb-4">
              <p className="text-sm text-slate-600 dark:text-slate-300">📍 {selectedZona.referencia}</p>
              <p className="text-sm text-slate-600 dark:text-slate-300">🚶 {selectedZona.distancia_min} min</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">{formatUpdatedAt(selectedZona.updatedAt)}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">{getConfianzaLabel(getConfianza(selectedZona.estado))}</p>
            </div>
            <button onClick={() => abrirMapa(selectedZona)} className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 flex items-center justify-center gap-2"><Map size={20} /> Iniciar ruta</button>
            <button onClick={() => setSelectedZona(null)} className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold flex items-center justify-center gap-2"><X size={16} /> Cerrar</button>
          </div>
        </>
      )}
    </div>
  )
}

export default Salir
