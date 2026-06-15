import { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Map, X, List, Info } from 'lucide-react'
import { InteractiveMap } from '@/components/InteractiveMap'
import {
  getSalidasOrdenadas,
  getModoSalida,
  calcularScoreSalida
} from '@/data/mockSalidas'
import { useAppStore } from '@/core/state/store'
import { mapZonesToSalidas, type ZonaSalida } from '@/data/mappers'
import { getConfianza, getConfianzaLabel } from '@/utils/confianza'
import { formatUpdatedAt } from '@/utils/formatTime'
import {
  crearExitSession,
  puedeCambiarModo,
  aplicarCambioModo,
  type ExitSessionState
} from '@/utils/exitSessionController'
import { getDistancias, haversine } from '@/utils/geo'

type TipoTransporte = 'auto' | 'transporte' | 'peatonal'

const Salir = () => {
  const navigate = useNavigate()
  const zones = useAppStore(s => s.zones)
  const [tipo, setTipo] = useState<TipoTransporte>('auto')
  const [selectedZona, setSelectedZona] = useState<ZonaSalida | null>(null)
  const [showMap, setShowMap] = useState(false)
  const userLocation = useAppStore(s => s.userLocation)

  const zonasMock = useMemo(() => mapZonesToSalidas(zones), [zones])

  // Modo inicial desde engine
  const modoInicial = getModoSalida(zonasMock, tipo)
  const [session, setSession] = useState<ExitSessionState>(
    crearExitSession(modoInicial)
  )

  // Reset de sesión cuando cambia el escenario
  useEffect(() => {
    const modoInicial = getModoSalida(zonasMock, tipo)
    setSession(crearExitSession(modoInicial))
  }, [zonasMock, tipo])

  const salidasOrdenadas = useMemo(() => {
    const ordenadas = getSalidasOrdenadas(zonasMock, tipo)
    if (userLocation) {
      return [...ordenadas].sort((a, b) => {
        if (a.lat && a.lng && b.lat && b.lng) {
          const distA = haversine(userLocation[0], userLocation[1], a.lat, a.lng)
          const distB = haversine(userLocation[0], userLocation[1], b.lat, b.lng)
          return distA - distB
        }
        return 0
      })
    }
    return ordenadas
  }, [zonasMock, tipo, userLocation])

  const salidasModo = useMemo(() => {
    const filtradas = zonasMock.filter(salida => salida.transporte === tipo)
    const ordenadas = filtradas.length > 0 ? getSalidasOrdenadas(filtradas, tipo) : ([salidasOrdenadas[0]].filter(Boolean) as ZonaSalida[])
    if (userLocation) {
      return [...ordenadas].sort((a, b) => {
        if (a.lat && a.lng && b.lat && b.lng) {
          const distA = haversine(userLocation[0], userLocation[1], a.lat, a.lng)
          const distB = haversine(userLocation[0], userLocation[1], b.lat, b.lng)
          return distA - distB
        }
        return 0
      })
    }
    return ordenadas
  }, [zonasMock, tipo, salidasOrdenadas, userLocation])

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

    setSession(prev => {
      if (puedeCambiarModo(nuevoModo, prev)) {
        console.log('modo_cambiado', {
          anterior: prev.modoActual,
          nuevo: nuevoModo,
          timestamp: Date.now()
        })
        return aplicarCambioModo(nuevoModo, prev)
      } else {
        console.log('cambio_rechazado', {
          actual: prev.modoActual,
          sugerido: nuevoModo,
          razon: nuevoModo === prev.modoActual ? 'mismo_modo' : 'cooldown_activo'
        })
        return prev
      }
    })
  }, [tipo, zonasMock])

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
      case 'colapsado': return 'bg-gray-500/20 text-gray-500 dark:text-gray-300'
      default: return 'bg-gray-500/20 text-gray-500 dark:text-gray-300'
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
    <div className="bg-white dark:bg-slate-800 px-4 py-3 shadow-sm z-10 relative">
      <p className="text-sm text-slate-600 dark:text-slate-300 text-center font-medium">
        ℹ️ Te mostramos la forma más rápida de salir según el flujo actual
      </p>
    </div>
  )

  if (showMap) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Salir" showBack onBack={() => navigate('/')} />
        {salirDescription}
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          {/* Selector tipo */}
          <div className="grid grid-cols-3 gap-2">
            {(['auto', 'transporte', 'peatonal'] as TipoTransporte[]).map(t => (
              <button
                key={t}
                onClick={() => setTipo(t)}
                className={`p-3 rounded-xl font-bold transition-transform active:scale-95 text-sm ${
                  tipo === t ? 'bg-primary text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
                }`}
              >
                {t === 'auto' ? '🚗 Auto' : t === 'transporte' ? '🚌 Transporte' : '🚶 Caminando'}
              </button>
            ))}
          </div>

          <InteractiveMap
            puntos={salidasModo
              .filter(z => z.lat && z.lng)
              .map(z => ({
                id: z.id,
                nombre: z.nombre,
                lat: z.lat!,
                lng: z.lng!,
                referencia: z.referencia,
                tipo: 'salida',
                originalData: z
              }))}
            onSelectPunto={(p) => setSelectedZona(p as ZonaSalida)}
            onUserLocationUpdate={() => {}}
          />

          {/* Lista de salidas */}
          <div className="space-y-2 pb-16">
            <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 flex justify-between">
              <span>📍 {salidasModo.length} salidas disponibles ({tipo === 'auto' ? 'Auto' : tipo === 'transporte' ? 'Transporte' : 'Caminando'})</span>
              {userLocation && <span className="text-blue-500 text-[10px] font-semibold">📡 Ubicación GPS activa</span>}
            </p>
            {salidasModo.map(zona => {
              const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min)
              return (
                <button
                  key={zona.id}
                  onClick={() => setSelectedZona(zona)}
                  className="w-full text-left bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors group shadow-sm flex items-start gap-2"
                >
                  <span className="text-lg mt-0.5">
                    {tipo === 'auto' ? '🚗' : tipo === 'transporte' ? '🚌' : '🚶'}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center">
                      <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">
                        {zona.nombre}
                      </p>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getEstadoStyles(zona.estado)}`}>
                        {getEstadoLabel(zona.estado)}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 flex flex-wrap gap-x-2 gap-y-0.5 items-center">
                      <span>🚶 {dist.walking}</span>
                      <span className="opacity-50">·</span>
                      <span>🚗 {dist.driving}</span>
                      {zona.espera_min > 0 && (
                        <>
                          <span className="opacity-50">·</span>
                          <span>⏱️ {zona.espera_min} min espera</span>
                        </>
                      )}
                      <span className="opacity-50">·</span>
                      <span className="truncate">{zona.referencia}</span>
                    </p>
                  </div>
                  <Info size={16} className="text-slate-400 flex-shrink-0" />
                </button>
              )
            })}
          </div>
        </div>

        {/* Botón flotante para alternar Mapa/Lista */}
        <button
          onClick={() => setShowMap(false)}
          className="fixed bottom-4 right-4 bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 px-4 rounded-full font-bold shadow-lg flex items-center gap-2 z-30 transition-transform active:scale-95 text-sm"
        >
          <List size={20} />
          Ver lista
        </button>

        {/* Bottom Sheet */}
        {selectedZona && (
          <>
            <div
              className="fixed inset-0 bg-black/50 z-[9999]"
              onClick={() => setSelectedZona(null)}
            />
            <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl">
              <div
                className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
                onClick={() => setSelectedZona(null)}
              />

              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
                {selectedZona.nombre}
              </h3>

              <div className="space-y-2 mb-4">
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  📍 {selectedZona.referencia}
                </p>
                {(() => {
                  const dist = getDistancias(selectedZona.lat ?? 0, selectedZona.lng ?? 0, userLocation, selectedZona.distancia_min)
                  return (
                    <>
                      <p className="text-sm text-slate-600 dark:text-slate-300">
                        🚶 Tiempo caminando: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span>
                      </p>
                      <p className="text-sm text-slate-600 dark:text-slate-300">
                        🚗 Tiempo en auto: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span>
                      </p>
                    </>
                  )
                })()}
                <p className="text-xs text-slate-500 dark:text-slate-300">
                  {formatUpdatedAt(selectedZona.updatedAt)}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-300">
                  {getConfianzaLabel(getConfianza(selectedZona.estado))}
                </p>
              </div>

              <button
                onClick={() => abrirMapa(selectedZona)}
                className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2"
              >
                <Map size={20} />
                Iniciar ruta
              </button>

              <button
                onClick={() => setSelectedZona(null)}
                className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold transition-transform active:scale-95 flex items-center justify-center gap-2"
              >
                <X size={16} />
                Cerrar
              </button>
            </div>
          </>
        )}
      </div>
    )
  }

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
                {(() => {
                  const dist = getDistancias(principal.lat ?? 0, principal.lng ?? 0, userLocation, principal.distancia_min)
                  return (
                    <p className="text-sm text-slate-600 dark:text-slate-300 flex gap-3">
                      <span>🚶 {dist.walking}</span>
                      <span>🚗 {dist.driving}</span>
                      {principal.espera_min > 0 && <span>⏱️ {principal.espera_min} min espera</span>}
                    </p>
                  )
                })()}
                <p className="text-xs text-slate-500 dark:text-slate-300 mt-2">{getEstadoLabel(principal.estado)}</p>
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

        {/* Botón flotante para alternar Mapa/Lista */}
        <button
          onClick={() => setShowMap(true)}
          className="fixed bottom-4 right-4 bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 px-4 rounded-full font-bold shadow-lg flex items-center gap-2 z-30 transition-transform active:scale-95 text-sm"
        >
          <Map size={20} />
          Ver mapa completo
        </button>

        {/* Bottom Sheet */}
        {selectedZona && (
          <>
            <div
              className="fixed inset-0 bg-black/50 z-[9999]"
              onClick={() => setSelectedZona(null)}
            />
            <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl">
              <div
                className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
                onClick={() => setSelectedZona(null)}
              />

              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
                {selectedZona.nombre}
              </h3>

              <div className="space-y-2 mb-4">
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  📍 {selectedZona.referencia}
                </p>
                {(() => {
                  const dist = getDistancias(selectedZona.lat ?? 0, selectedZona.lng ?? 0, userLocation, selectedZona.distancia_min)
                  return (
                    <>
                      <p className="text-sm text-slate-600 dark:text-slate-300">🚶 Caminando: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span></p>
                      <p className="text-sm text-slate-600 dark:text-slate-300">🚗 En auto: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span></p>
                    </>
                  )
                })()}
                <p className="text-xs text-slate-500 dark:text-slate-300">
                  {formatUpdatedAt(selectedZona.updatedAt)}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-300">
                  {getConfianzaLabel(getConfianza(selectedZona.estado))}
                </p>
              </div>

              <button
                onClick={() => abrirMapa(selectedZona)}
                className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2"
              >
                <Map size={20} />
                Iniciar ruta
              </button>

              <button
                onClick={() => setSelectedZona(null)}
                className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold transition-transform active:scale-95 flex items-center justify-center gap-2"
              >
                <X size={16} />
                Cerrar
              </button>
            </div>
          </>
        )}
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
                {(() => {
                  const dist = getDistancias(principal.lat ?? 0, principal.lng ?? 0, userLocation, principal.distancia_min)
                  return (
                    <p className="text-sm opacity-90 flex gap-3">
                      <span>🚶 {dist.walking}</span>
                      <span>🚗 {dist.driving}</span>
                    </p>
                  )
                })()}
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
                {(() => {
                  const dist = getDistancias(alternativa.lat ?? 0, alternativa.lng ?? 0, userLocation, alternativa.distancia_min)
                  return (
                    <p className="text-sm text-slate-600 dark:text-slate-300 flex gap-3">
                      <span>🚶 {dist.walking}</span>
                      <span>🚗 {dist.driving}</span>
                    </p>
                  )
                })()}
              </div>
            </button>
          )}

          <p className="text-xs text-slate-400 dark:text-slate-400 text-center">
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

      {/* Botón flotante para alternar Mapa/Lista */}
      <button
        onClick={() => setShowMap(true)}
        className="fixed bottom-4 right-4 bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 px-4 rounded-full font-bold shadow-lg flex items-center gap-2 z-30 transition-transform active:scale-95 text-sm"
      >
        <Map size={20} />
        Ver mapa completo
      </button>

      {/* Bottom Sheet */}
      {selectedZona && (
        <>
          <div className="fixed inset-0 bg-black/50 z-[9999]" onClick={() => setSelectedZona(null)} />
          <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl">
            <div className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer" onClick={() => setSelectedZona(null)} />
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">{selectedZona.nombre}</h3>
            <div className="space-y-2 mb-4">
              <p className="text-sm text-slate-600 dark:text-slate-300">📍 {selectedZona.referencia}</p>
              {(() => {
                const dist = getDistancias(selectedZona.lat ?? 0, selectedZona.lng ?? 0, userLocation, selectedZona.distancia_min)
                return (
                  <>
                    <p className="text-sm text-slate-600 dark:text-slate-300">🚶 Caminando: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span></p>
                    <p className="text-sm text-slate-600 dark:text-slate-300">🚗 En auto: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span></p>
                  </>
                )
              })()}
              <p className="text-xs text-slate-500 dark:text-slate-300">{formatUpdatedAt(selectedZona.updatedAt)}</p>
              <p className="text-xs text-slate-500 dark:text-slate-300">{getConfianzaLabel(getConfianza(selectedZona.estado))}</p>
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
                {(() => {
                  const dist = getDistancias(principal.lat ?? 0, principal.lng ?? 0, userLocation, principal.distancia_min)
                  return (
                    <p className="text-sm text-slate-600 dark:text-slate-300 flex gap-3">
                      <span>🚶 {dist.walking}</span>
                      <span>🚗 {dist.driving}</span>
                    </p>
                  )
                })()}
                <p className="text-xs text-slate-500 dark:text-slate-300 mt-2">Menor tiempo total de salida</p>
                <p className="text-xs text-slate-500 dark:text-slate-300 mt-2">{formatUpdatedAt(principal.updatedAt)}</p>
                <p className="text-xs text-slate-500 dark:text-slate-300 mt-1">{getConfianzaLabel(getConfianza(principal.estado))}</p>
              </div>
            </button>
          )}

          {alternativa && (
            <button onClick={() => setSelectedZona(alternativa)} className="w-full">
              <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
                <p className="font-bold text-slate-800 dark:text-slate-100">Alternativa: {alternativa.nombre}</p>
                <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">📍 {alternativa.referencia}</p>
                {(() => {
                  const dist = getDistancias(alternativa.lat ?? 0, alternativa.lng ?? 0, userLocation, alternativa.distancia_min)
                  return (
                    <p className="text-sm text-slate-600 dark:text-slate-300 flex gap-3">
                      <span>🚶 {dist.walking}</span>
                      <span>🚗 {dist.driving}</span>
                    </p>
                  )
                })()}
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

      {/* Botón flotante para alternar Mapa/Lista */}
      <button
        onClick={() => setShowMap(true)}
        className="fixed bottom-4 right-4 bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 px-4 rounded-full font-bold shadow-lg flex items-center gap-2 z-30 transition-transform active:scale-95 text-sm"
      >
        <Map size={20} />
        Ver mapa completo
      </button>

      {/* Bottom Sheet */}
      {selectedZona && (
        <>
          <div className="fixed inset-0 bg-black/50 z-[9999]" onClick={() => setSelectedZona(null)} />
          <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl">
            <div className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer" onClick={() => setSelectedZona(null)} />
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">{selectedZona.nombre}</h3>
            <div className="space-y-2 mb-4">
              <p className="text-sm text-slate-600 dark:text-slate-300">📍 {selectedZona.referencia}</p>
              {(() => {
                const dist = getDistancias(selectedZona.lat ?? 0, selectedZona.lng ?? 0, userLocation, selectedZona.distancia_min)
                return (
                  <>
                    <p className="text-sm text-slate-600 dark:text-slate-300">🚶 Caminando: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span></p>
                    <p className="text-sm text-slate-600 dark:text-slate-300">🚗 En auto: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span></p>
                  </>
                )
              })()}
              <p className="text-xs text-slate-500 dark:text-slate-300">{formatUpdatedAt(selectedZona.updatedAt)}</p>
              <p className="text-xs text-slate-500 dark:text-slate-300">{getConfianzaLabel(getConfianza(selectedZona.estado))}</p>
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
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-2 mb-4">
            🟢 Bajo: rápido · 🟡 Medio: demora moderada · 🔴 Alto: mucha demora
          </div>
          <div className="space-y-3">
            {salidasModo.slice(0, 3).map(zona => {
              const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min)
              return (
              <button key={zona.id} onClick={() => setSelectedZona(zona)}
                className="w-full p-4 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-left hover:border-primary transition-colors">
                <div className="flex justify-between items-center">
                  <span className="font-bold mr-2 text-gray-900 dark:text-gray-100">{zona.nombre}</span>
                  <span className={`px-2 py-1 rounded text-xs font-bold whitespace-nowrap shrink-0 ${getEstadoStyles(zona.estado)}`}>{getEstadoLabel(zona.estado)}</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">📍 {zona.referencia}</p>
                <p className="text-sm text-gray-600 dark:text-gray-300 flex flex-wrap gap-x-3 gap-y-0.5">
                  <span>🚶 {dist.walking}</span>
                  <span>🚗 {dist.driving}</span>
                  {zona.espera_min > 0 && <span>⏱️ {zona.espera_min} min espera</span>}
                </p>
                <p className="text-xs text-gray-400 dark:text-gray-300 mt-1">{formatUpdatedAt(zona.updatedAt)}</p>
                <p className="text-xs text-slate-500 dark:text-slate-300 mt-1">{getConfianzaLabel(getConfianza(zona.estado))}</p>
              </button>
              )
            })}
          </div>
        </div>

        {principal && (
          <button onClick={() => abrirMapa(principal)}
            className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2">
            <Map size={20} /> Iniciar ruta
          </button>
        )}
      </div>

      {/* Botón flotante para alternar Mapa/Lista */}
      <button
        onClick={() => setShowMap(true)}
        className="fixed bottom-4 right-4 bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 px-4 rounded-full font-bold shadow-lg flex items-center gap-2 z-30 transition-transform active:scale-95 text-sm"
      >
        <Map size={20} />
        Ver mapa completo
      </button>

      {/* Bottom Sheet */}
      {selectedZona && (
        <>
          <div className="fixed inset-0 bg-black/50 z-[9999]" onClick={() => setSelectedZona(null)} />
          <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl">
            <div className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer" onClick={() => setSelectedZona(null)} />
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">{selectedZona.nombre}</h3>
            <div className="space-y-2 mb-4">
              <p className="text-sm text-slate-600 dark:text-slate-300">📍 {selectedZona.referencia}</p>
              {(() => {
                const dist = getDistancias(selectedZona.lat ?? 0, selectedZona.lng ?? 0, userLocation, selectedZona.distancia_min)
                return (
                  <>
                    <p className="text-sm text-slate-600 dark:text-slate-300">🚶 Caminando: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span></p>
                    <p className="text-sm text-slate-600 dark:text-slate-300">🚗 En auto: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span></p>
                  </>
                )
              })()}
              <p className="text-xs text-slate-500 dark:text-slate-300">{formatUpdatedAt(selectedZona.updatedAt)}</p>
              <p className="text-xs text-slate-500 dark:text-slate-300">{getConfianzaLabel(getConfianza(selectedZona.estado))}</p>
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
