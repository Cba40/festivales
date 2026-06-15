import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Map, List, X, Info } from 'lucide-react'
import { InteractiveMap } from '@/components/InteractiveMap'
import {
  getComidaOrdenada,
  getModoComer,
} from '@/data/mockComer'
import { useAppStore } from '@/core/state/store'
import { mapZonesToComida } from '@/data/mappers'
import { getConfianza, getConfianzaLabel } from '@/utils/confianza'
import { formatUpdatedAt } from '@/utils/formatTime'
import type { PuntoComida } from '@/data/mappers'
import { getDistancias, haversine } from '@/utils/geo'

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

const ServiciosComer = () => {
  const navigate = useNavigate()
  const zones = useAppStore(s => s.zones)
  const [selectedPunto, setSelectedPunto] = useState<PuntoComida | null>(null)
  const [mostrarOpciones, setMostrarOpciones] = useState(false)
  const [showMap, setShowMap] = useState(false)
  const userLocation = useAppStore(s => s.userLocation)

  const comidas = useMemo(() => mapZonesToComida(zones), [zones])

  const comidasOrdenadas = useMemo(() => {
    const ordenadas = getComidaOrdenada(comidas)
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
  }, [comidas, userLocation])

  const modo = useMemo(() => getModoComer(comidas), [comidas])

  const principal = comidasOrdenadas[0]
  const alternativa = comidasOrdenadas[1]

  const abrirMapa = (punto: PuntoComida) => {
    if (punto.lat && punto.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${punto.lat},${punto.lng}`,
        '_blank'
      )
    }
    setSelectedPunto(null)
  }

  // Bottom Sheet compartido
  const renderBottomSheet = selectedPunto && (
    <>
      <div
        className="fixed inset-0 bg-black/50 z-[9999]"
        onClick={() => setSelectedPunto(null)}
      />
      <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl">
        <div
          className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
          onClick={() => setSelectedPunto(null)}
        />

        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
          {selectedPunto.nombre}
        </h3>

        <div className="space-y-2 mb-4">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            📍 {selectedPunto.referencia}
          </p>
          {(() => {
            const dist = getDistancias(selectedPunto.lat ?? 0, selectedPunto.lng ?? 0, userLocation, selectedPunto.distancia_min)
            return (
              <>
                <p className="text-sm text-slate-600 dark:text-slate-300">🚶 Caminando: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span></p>
                <p className="text-sm text-slate-600 dark:text-slate-300">🚗 En auto: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span></p>
              </>
            )
          })()}
          <p className="text-sm text-slate-600 dark:text-slate-300">
            ⏱️ Espera: {selectedPunto.espera_min} min
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {formatUpdatedAt(selectedPunto.updatedAt)}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {getConfianzaLabel(getConfianza(selectedPunto.estado))}
          </p>
        </div>

        <button
          onClick={() => abrirMapa(selectedPunto)}
          className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2"
        >
          <Map size={20} />
          Iniciar ruta
        </button>

        <button
          onClick={() => setSelectedPunto(null)}
          className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold transition-transform active:scale-95 flex items-center justify-center gap-2"
        >
          <X size={16} />
          Cerrar
        </button>
      </div>
    </>
  )

  // Botón flotante "Ver mapa completo" / "Ver lista"
  const botonMapa = (
    <button
      onClick={() => setShowMap(v => !v)}
      className="fixed bottom-4 right-4 bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 px-4 rounded-full font-bold shadow-lg flex items-center gap-2 z-30 transition-transform active:scale-95 text-sm"
    >
      {showMap ? <List size={20} /> : <Map size={20} />}
      {showMap ? 'Ver lista' : 'Ver mapa completo'}
    </button>
  )

  // Vista mapa completo (aplica en todos los modos)
  if (showMap) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          <InteractiveMap
            puntos={comidasOrdenadas
              .filter(p => p.lat && p.lng)
              .map(p => ({
                id: p.id,
                nombre: p.nombre,
                lat: p.lat!,
                lng: p.lng!,
                referencia: p.referencia,
                tipo: 'comer',
                originalData: p
              }))}
            onSelectPunto={(p) => setSelectedPunto(p as PuntoComida)}
            onUserLocationUpdate={() => {}}
          />

          {/* Lista debajo del mapa */}
          <div className="space-y-2 pb-20">
            <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 flex justify-between">
              <span>🍔 {comidasOrdenadas.length} zonas gastronómicas</span>
              {userLocation && <span className="text-blue-500 text-[10px] font-semibold">📡 Ubicación GPS activa</span>}
            </p>
            {comidasOrdenadas.map(punto => {
              const dist = getDistancias(punto.lat ?? 0, punto.lng ?? 0, userLocation, punto.distancia_min)
              return (
                <button
                  key={punto.id}
                  onClick={() => setSelectedPunto(punto)}
                  className="w-full text-left bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-orange-400 dark:hover:border-orange-500 transition-colors group shadow-sm flex items-start gap-2"
                >
                  <span className="text-lg mt-0.5">🍔</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center">
                      <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-orange-600 dark:group-hover:text-orange-400 truncate">
                        {punto.nombre}
                      </p>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getEstadoStyles(punto.estado)}`}>
                        {getEstadoLabel(punto.estado)}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 flex flex-wrap gap-x-2 gap-y-0.5 items-center">
                      <span>🚶 {dist.walking}</span>
                      <span className="opacity-50">·</span>
                      <span>🚗 {dist.driving}</span>
                      <span className="opacity-50">·</span>
                      <span>⏱️ {punto.espera_min} min espera</span>
                    </p>
                  </div>
                  <Info size={16} className="text-slate-400 flex-shrink-0" />
                </button>
              )
            })}
          </div>
        </div>

        {botonMapa}
        {renderBottomSheet}
      </div>
    )
  }

  // SIN SOLUCIÓN
  if (modo === 'sin_solucion') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 space-y-4">
          <div className="bg-danger text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">🚧 No hay opciones convenientes para comer</p>
            <p className="text-sm mt-2 opacity-90">Alta demanda en todas las zonas gastronómicas</p>
          </div>

          <div className="bg-slate-100 dark:bg-slate-700 p-4 rounded-xl space-y-3">
            <button className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform">
              ⏱️ Esperar 20–30 min
            </button>
            <button className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform">
              🚶 Explorar otra zona
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
              {comidasOrdenadas.slice(0, 2).map((punto) => {
                const dist = getDistancias(punto.lat ?? 0, punto.lng ?? 0, userLocation, punto.distancia_min)
                return (
                  <button
                    key={punto.id}
                    onClick={() => setSelectedPunto(punto)}
                    className="w-full p-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg text-left"
                  >
                    <span className="font-bold text-gray-900 dark:text-gray-100">{punto.nombre}</span>
                    <span className={`ml-2 px-2 py-1 rounded text-xs font-bold ${getEstadoStyles(punto.estado)}`}>
                      {getEstadoLabel(punto.estado)}
                    </span>
                    <p className="text-xs text-gray-500 dark:text-gray-300 mt-1 flex flex-wrap gap-x-2">
                      <span>🚶 {dist.walking}</span>
                      <span>🚗 {dist.driving}</span>
                      <span>⏱️ {punto.espera_min} min</span>
                    </p>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {botonMapa}
        {renderBottomSheet}
      </div>
    )
  }

  // GUIAR
  if (modo === 'guiar') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/')} />

        <div className="bg-danger text-white px-4 py-3">
          <h2 className="font-bold text-lg">👉 Zona gastronómica saturada</h2>
        </div>

        <div className="flex-1 p-4 space-y-4">
          {principal && (() => {
            const dist = getDistancias(principal.lat ?? 0, principal.lng ?? 0, userLocation, principal.distancia_min)
            return (
              <button onClick={() => setSelectedPunto(principal)} className="w-full">
                <div className="bg-primary text-white p-6 rounded-xl text-left shadow-lg">
                  <p className="text-lg font-bold">👉 Dirigite ahora a {principal.nombre}</p>
                  <p className="text-sm opacity-90 mt-2">📍 {principal.referencia}</p>
                  <p className="text-sm opacity-90 flex gap-3">
                    <span>🚶 {dist.walking}</span>
                    <span>🚗 {dist.driving}</span>
                  </p>
                  <p className="text-sm opacity-90">⏱️ Espera: {principal.espera_min} min</p>
                  {principal.estado === 'alto' && (
                    <p className="text-xs opacity-75 mt-2">⚠️ Últimos lugares</p>
                  )}
                </div>
              </button>
            )
          })()}

          {alternativa && principal?.estado !== 'colapsado' && (() => {
            const dist = getDistancias(alternativa.lat ?? 0, alternativa.lng ?? 0, userLocation, alternativa.distancia_min)
            return (
              <button onClick={() => setSelectedPunto(alternativa)} className="w-full">
                <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
                  <p className="font-bold text-slate-800 dark:text-slate-100">👉 Si está lleno → {alternativa.nombre}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">📍 {alternativa.referencia}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-300 flex gap-3">
                    <span>🚶 {dist.walking}</span>
                    <span>🚗 {dist.driving}</span>
                    <span>⏱️ {alternativa.espera_min} min</span>
                  </p>
                </div>
              </button>
            )
          })()}

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

        {botonMapa}
        {renderBottomSheet}
      </div>
    )
  }

  // ASISTIR
  if (modo === 'asistir') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 space-y-4">
          {principal && (() => {
            const dist = getDistancias(principal.lat ?? 0, principal.lng ?? 0, userLocation, principal.distancia_min)
            return (
              <button onClick={() => setSelectedPunto(principal)} className="w-full">
                <div className="bg-white dark:bg-slate-800 border-l-4 border-primary p-4 rounded-xl text-left shadow-md">
                  <p className="font-bold text-slate-800 dark:text-slate-100 text-lg">👉 Mejor opción ahora: {principal.nombre}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-300 mt-2">📍 {principal.referencia}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-300 flex gap-3">
                    <span>🚶 {dist.walking}</span>
                    <span>🚗 {dist.driving}</span>
                    <span>⏱️ {principal.espera_min} min</span>
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-300 mt-2">{formatUpdatedAt(principal.updatedAt)}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-300 mt-1">{getConfianzaLabel(getConfianza(principal.estado))}</p>
                </div>
              </button>
            )
          })()}

          {alternativa && (() => {
            const dist = getDistancias(alternativa.lat ?? 0, alternativa.lng ?? 0, userLocation, alternativa.distancia_min)
            return (
              <button onClick={() => setSelectedPunto(alternativa)} className="w-full">
                <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
                  <p className="font-bold text-slate-800 dark:text-slate-100">Alternativa: {alternativa.nombre}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">📍 {alternativa.referencia}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-300 flex gap-3">
                    <span>🚶 {dist.walking}</span>
                    <span>🚗 {dist.driving}</span>
                    <span>⏱️ {alternativa.espera_min} min</span>
                  </p>
                </div>
              </button>
            )
          })()}

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

        {botonMapa}
        {renderBottomSheet}
      </div>
    )
  }

  // INFORMAR (default)
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Comer" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-md">
          <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4">
            Zonas gastronómicas disponibles
          </h2>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-2 mb-4">
            🟢 Bajo: rápido · 🟡 Medio: demora moderada · 🔴 Alto: mucha demora
          </div>
          {userLocation && (
            <p className="text-[10px] text-blue-500 font-semibold mb-3">📡 Ubicación GPS activa — lista ordenada por cercanía</p>
          )}
          <div className="space-y-3">
            {comidasOrdenadas.slice(0, 3).map((punto) => {
              const dist = getDistancias(punto.lat ?? 0, punto.lng ?? 0, userLocation, punto.distancia_min)
              return (
                <button
                  key={punto.id}
                  onClick={() => setSelectedPunto(punto)}
                  className="w-full p-4 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-left hover:border-primary dark:hover:border-primary/70 transition-colors"
                >
                  <div className="flex justify-between items-center">
                    <span className="font-bold mr-2 text-gray-900 dark:text-gray-100">{punto.nombre}</span>
                    <span className={`px-2 py-1 rounded text-xs font-bold whitespace-nowrap shrink-0 ${getEstadoStyles(punto.estado)}`}>
                      {getEstadoLabel(punto.estado)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">📍 {punto.referencia}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-300 flex flex-wrap gap-x-3 gap-y-0.5">
                    <span>🚶 {dist.walking}</span>
                    <span>🚗 {dist.driving}</span>
                    <span>⏱️ {punto.espera_min} min espera</span>
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-300 mt-1">{formatUpdatedAt(punto.updatedAt)}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-300 mt-1">{getConfianzaLabel(getConfianza(punto.estado))}</p>
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

      {botonMapa}
      {renderBottomSheet}
    </div>
  )
}

export default ServiciosComer
