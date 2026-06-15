import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Map, X, List, Info } from 'lucide-react'
import { InteractiveMap } from '@/components/InteractiveMap'
import {
  getZonasOrdenadas,
  getModoEstacionamiento,
  calcularScoreEstacionamiento,
} from '@/data/mockZones'
import { useAppStore } from '@/core/state/store'
import { mapZonesToEstacionamiento, type ZonaEstacionamiento } from '@/data/mappers'
import { getConfianza, getConfianzaLabel } from '@/utils/confianza'
import { formatUpdatedAt } from '@/utils/formatTime'
import { getEventoConfig } from '@/config/eventoConfig'
import { getUmbralContexto } from '@/utils/decisionEngine'
import { getHoraEvento } from '@/utils/contextoEvento'
import { getDistancias, haversine } from '@/utils/geo'

const Estacionar = () => {
  const navigate = useNavigate()
  const zones = useAppStore(s => s.zones)
  const [selectedZona, setSelectedZona] = useState<ZonaEstacionamiento | null>(null)
  const [mostrarOpciones, setMostrarOpciones] = useState(false)
  const [showMap, setShowMap] = useState(false)
  const userLocation = useAppStore(s => s.userLocation)

  const zonasMock = useMemo(() => {
    const mapped = mapZonesToEstacionamiento(zones)
    console.log('[Estacionar] zones from store:', zones.length, 'mapped:', mapped.length, mapped.map(z => ({ n: z.nombre, d: z.disponibilidad, e: z.estado })))
    return mapped
  }, [zones])

  const zonasOrdenadas = useMemo(() => {
    const ordenadas = getZonasOrdenadas(zonasMock)
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
  }, [zonasMock, userLocation])

  const modo = getModoEstacionamiento(zonasMock)
  console.log('[Estacionar] modo:', modo, 'mejor:', zonasOrdenadas[0]?.nombre, 'score:', zonasOrdenadas[0] && calcularScoreEstacionamiento(zonasOrdenadas[0]), 'hora:', getHoraEvento())

  const principal = zonasOrdenadas[0]
  const alternativaRaw = zonasOrdenadas[1]

  // Doble condición: mejora real vs principal Y bajo umbral contextual
  const h = getHoraEvento()
  const umbral = getUmbralContexto(h)
  const esAlternativaValida = alternativaRaw &&
    calcularScoreEstacionamiento(alternativaRaw) <
    Math.min(
      calcularScoreEstacionamiento(principal) * 0.85,
      umbral * 0.9
    )
  const alternativa = esAlternativaValida ? alternativaRaw : undefined

  const abrirMapa = (zona: ZonaEstacionamiento) => {
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
      case 'bajo':
        return 'bg-success/20 text-success'
      case 'medio':
        return 'bg-warning/20 text-warning'
      case 'alto':
        return 'bg-danger/20 text-danger'
      case 'colapsado':
        return 'bg-gray-500/20 text-gray-500 dark:text-gray-300'
      default:
        return 'bg-gray-500/20 text-gray-500 dark:text-gray-300'
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

  // MAPA COMPLETO
  if (showMap) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Estacionar" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          <InteractiveMap
            puntos={zonasOrdenadas
              .filter(z => z.lat && z.lng)
              .map(z => ({
                id: z.id,
                nombre: z.nombre,
                lat: z.lat!,
                lng: z.lng!,
                referencia: z.referencia,
                tipo: 'estacionamiento',
                originalData: z
              }))}
            onSelectPunto={(p) => setSelectedZona(p as ZonaEstacionamiento)}
            onUserLocationUpdate={() => {}}
          />

          {/* Lista de estacionamientos */}
          <div className="space-y-2 pb-16">
            <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 flex justify-between">
              <span>📍 {zonasOrdenadas.length} zonas disponibles</span>
              {userLocation && <span className="text-blue-500 text-[10px] font-semibold">📡 Ubicación GPS activa</span>}
            </p>
            {zonasOrdenadas.map(zona => {
              const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min)
              return (
                <button
                  key={zona.id}
                  onClick={() => setSelectedZona(zona)}
                  className="w-full text-left bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors group shadow-sm flex items-start gap-2"
                >
                  <span className="text-lg mt-0.5">🚗</span>
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
                      <span className="opacity-50">·</span>
                      <span>📊 {zona.disponibilidad}% disp.</span>
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
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  📊 Disponibilidad: {selectedZona.disponibilidad}%
                </p>
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
  if (modo === 'sin_solucion') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Estacionar" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 space-y-4">
          <div className="bg-danger text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">🚧 No hay opciones convenientes para estacionar</p>
            <p className="text-sm mt-2 opacity-90">Alta demanda en toda la zona</p>
          </div>

          <div className="bg-slate-100 dark:bg-slate-700 p-4 rounded-xl space-y-3">
            <button className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform">
              ⏱️ Esperar 20–30 min
            </button>
            <button className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform">
              🚶 Alejarse de esta zona
            </button>
          </div>

          <div className="mt-4 text-center space-y-2">
            <p className="text-xs text-slate-400 dark:text-slate-400">
              No hay opciones recomendadas en este momento
            </p>
            <button
              className="text-xs underline text-slate-500 dark:text-slate-300"
              onClick={() => setMostrarOpciones(true)}
            >
              Ver opciones igualmente
            </button>
          </div>

          {mostrarOpciones && (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-red-500 text-center">
                ⚠️ Disponibilidad muy baja — podés no encontrar lugar
              </p>
              {zonasOrdenadas.slice(0, 2).map((zona) => {
                const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min)
                return (
                <button
                  key={zona.id}
                  onClick={() => setSelectedZona(zona)}
                  className="w-full p-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg text-left"
                >
                  <span className="font-bold text-gray-900 dark:text-gray-100">{zona.nombre}</span>
                  <span className={`ml-2 px-2 py-1 rounded text-xs font-bold ${getEstadoStyles(zona.estado)}`}>
                    {getEstadoLabel(zona.estado)}
                  </span>
                  <p className="text-xs text-gray-500 dark:text-gray-300 mt-1 flex flex-wrap gap-x-2">
                    <span>🚶 {dist.walking}</span>
                    <span>🚗 {dist.driving}</span>
                    <span>📊 {zona.disponibilidad}%</span>
                  </p>
                </button>
                )
              })}
            </div>
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
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  📊 Disponibilidad: {selectedZona.disponibilidad}%
                </p>
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
  if (modo === 'guiar') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Estacionar" showBack onBack={() => navigate('/')} />

        <div className="bg-danger text-white px-4 py-3">
          <h2 className="font-bold text-lg">👉 Zona actual saturada</h2>
        </div>

        <div className="flex-1 p-4 space-y-4">
          {principal && (
            <button
              onClick={() => setSelectedZona(principal)}
              className="w-full"
            >
              <div className="bg-primary text-white p-6 rounded-xl text-left shadow-lg">
                <p className="text-lg font-bold">
                  👉 Dirigite ahora a {principal.nombre}
                </p>
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
                {principal.disponibilidad < 20 && (
                  <p className="text-xs opacity-75 mt-2">⚠️ Disponibilidad limitada</p>
                )}
              </div>
            </button>
          )}

          {alternativa && principal.estado !== 'colapsado' && (
            <button
              onClick={() => setSelectedZona(alternativa)}
              className="w-full"
            >
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
                      <span>📊 {alternativa.disponibilidad}% disp.</span>
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
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  📊 Disponibilidad: {selectedZona.disponibilidad}%
                </p>
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

  // ASISTIR
  if (modo === 'asistir') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Estacionar" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 space-y-4">
          {principal && (
            <button
              onClick={() => setSelectedZona(principal)}
              className="w-full"
            >
              <div className="bg-white dark:bg-slate-800 border-l-4 border-primary p-4 rounded-xl text-left shadow-md">
                <p className="font-bold text-slate-800 dark:text-slate-100 text-lg">
                  👉 Mejor opción ahora: {principal.nombre}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300 mt-2">
                  📍 {principal.referencia}
                </p>
                {(() => {
                  const dist = getDistancias(principal.lat ?? 0, principal.lng ?? 0, userLocation, principal.distancia_min)
                  return (
                    <p className="text-sm text-slate-600 dark:text-slate-300 flex gap-3">
                      <span>🚶 {dist.walking}</span>
                      <span>🚗 {dist.driving}</span>
                      <span>📊 {principal.disponibilidad}% disp.</span>
                    </p>
                  )
                })()}
                <p className="text-xs text-slate-500 dark:text-slate-300 mt-2">
                  {formatUpdatedAt(principal.updatedAt)}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-300 mt-1">
                  {getConfianzaLabel(getConfianza(principal.estado))}
                </p>
              </div>
            </button>
          )}

          {alternativa && (
            <button
              onClick={() => setSelectedZona(alternativa)}
              className="w-full"
            >
              <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
                <p className="font-bold text-slate-800 dark:text-slate-100">
                  Alternativa: {alternativa.nombre}
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
                      <span>📊 {alternativa.disponibilidad}% disp.</span>
                    </p>
                  )
                })()}
              </div>
            </button>
          )}

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
              <p className="text-sm text-slate-600 dark:text-slate-300">
                📊 Disponibilidad: {selectedZona.disponibilidad}%
              </p>
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

  // INFORMAR
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Estacionar" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-md">
          <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4">
            Zonas disponibles
          </h2>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-2 mb-4">
            🟢 Bajo: rápido · 🟡 Medio: demora moderada · 🔴 Alto: mucha demora
          </div>
          <div className="space-y-3">
            {zonasOrdenadas.slice(0, 3).map((zona) => {
              const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min)
              return (
              <button
                key={zona.id}
                onClick={() => setSelectedZona(zona)}
                className="w-full p-4 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-left hover:border-primary dark:hover:border-primary/70 transition-colors"
              >
                <div className="flex justify-between items-center">
                  <span className="font-bold mr-2 text-gray-900 dark:text-gray-100">
                    {zona.nombre}
                  </span>
                  <span
                    className={`px-2 py-1 rounded text-xs font-bold whitespace-nowrap shrink-0 ${getEstadoStyles(zona.estado)}`}
                  >
                    {getEstadoLabel(zona.estado)}
                  </span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                  📍 {zona.referencia}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-300 flex flex-wrap gap-x-3 gap-y-0.5">
                  <span>🚶 {dist.walking}</span>
                  <span>🚗 {dist.driving}</span>
                  <span>📊 {zona.disponibilidad}% disp.</span>
                </p>
                <p className="text-xs text-gray-400 dark:text-gray-300 mt-1">
                  {formatUpdatedAt(zona.updatedAt)}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-300 mt-1">
                  {getConfianzaLabel(getConfianza(zona.estado))}
                </p>
              </button>
              )
            })}
          </div>
        </div>

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
              <p className="text-sm text-slate-600 dark:text-slate-300">
                📊 Disponibilidad: {selectedZona.disponibilidad}%
              </p>
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

export default Estacionar
