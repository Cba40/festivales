import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Map, List, X, Info } from 'lucide-react'
import { InteractiveMap } from '@/components/InteractiveMap'
import { useAppStore } from '@/core/state/store'
import { useGastronomyRecommendations, type ZonaGastronomicaItem } from '@/services/gastronomyProduct'
import { formatUpdatedAt } from '@/utils/formatTime'
import { getDistancias } from '@/utils/geo'

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

const getConfianzaLabel = (confidence: number): string => {
  if (confidence >= 0.7) return '✅ Alta probabilidad'
  if (confidence >= 0.4) return '⚠️ Últimos lugares'
  return '❗ Disponibilidad incierta'
}

const ServiciosComer = () => {
  const navigate = useNavigate()
  const { data, loading, error, refresh } = useGastronomyRecommendations()
  const [selectedZona, setSelectedZona] = useState<ZonaGastronomicaItem | null>(null)
  const [mostrarOpciones, setMostrarOpciones] = useState(false)
  const [showMap, setShowMap] = useState(false)
  const userLocation = useAppStore(s => s.userLocation)

  useEffect(() => {
    refresh()
  }, [refresh])

  const zonas = data?.zonas ?? []

  const modo = data?.mode ?? 'informar'

  const principal = zonas[0]
  const alternativa = zonas[1]

  const abrirMapa = (zona: ZonaGastronomicaItem) => {
    if (zona.lat && zona.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${zona.lat},${zona.lng}`,
        '_blank'
      )
    }
    setSelectedZona(null)
  }

  const renderBottomSheet = selectedZona && (
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
          {selectedZona.name}
        </h3>

        <div className="space-y-2 mb-4">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            📍 {selectedZona.referencia}
          </p>
          {(() => {
            const dist = getDistancias(selectedZona.lat ?? 0, selectedZona.lng ?? 0, userLocation, selectedZona.distancia_min ?? 5)
            return (
              <>
                <p className="text-sm text-slate-600 dark:text-slate-300">🚶 Caminando: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span></p>
                <p className="text-sm text-slate-600 dark:text-slate-300">🚗 En auto: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span></p>
              </>
            )
          })()}
          <p className="text-sm text-slate-600 dark:text-slate-300">
            ⏱️ Espera: {selectedZona.estimated_wait} min
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {formatUpdatedAt(Date.now())}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {getConfianzaLabel(selectedZona.confidence)}
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
  )

  const botonMapa = (
    <button
      onClick={() => setShowMap(v => !v)}
      className="fixed bottom-4 right-4 bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 px-4 rounded-full font-bold shadow-lg flex items-center gap-2 z-30 transition-transform active:scale-95 text-sm"
    >
      {showMap ? <List size={20} /> : <Map size={20} />}
      {showMap ? 'Ver lista' : 'Ver mapa completo'}
    </button>
  )

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/')} />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-500">Cargando recomendaciones...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/')} />
        <div className="flex-1 p-4 flex flex-col items-center justify-center space-y-4">
          <p className="text-danger font-bold">Error al cargar</p>
          <p className="text-sm text-slate-500 text-center">{error}</p>
          <button
            onClick={refresh}
            className="bg-primary text-white px-6 py-2 rounded-lg font-bold"
          >
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  if (showMap) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          <InteractiveMap
            puntos={zonas
              .filter(z => z.lat && z.lng)
              .map(z => ({
                id: z.zone_id,
                nombre: z.name,
                lat: z.lat!,
                lng: z.lng!,
                referencia: z.referencia,
                tipo: 'comer',
                originalData: z
              }))}
            onSelectPunto={(p) => setSelectedZona(p as ZonaGastronomicaItem)}
            onUserLocationUpdate={() => {}}
          />

          <div className="space-y-2 pb-20">
            <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 flex justify-between">
              <span>🍔 {zonas.length} zonas gastronómicas</span>
              {userLocation && <span className="text-blue-500 text-[10px] font-semibold">📡 Ubicación GPS activa</span>}
            </p>
            {zonas.map(zona => {
              const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min ?? 5)
              return (
                <button
                  key={zona.zone_id}
                  onClick={() => setSelectedZona(zona)}
                  className="w-full text-left bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-orange-400 dark:hover:border-orange-500 transition-colors group shadow-sm flex items-start gap-2"
                >
                  <span className="text-lg mt-0.5">🍔</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center">
                      <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-orange-600 dark:group-hover:text-orange-400 truncate">
                        {zona.name}
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
                      <span>⏱️ {zona.estimated_wait} min espera</span>
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
              {zonas.slice(0, 2).map((zona) => {
                const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min ?? 5)
                return (
                  <button
                    key={zona.zone_id}
                    onClick={() => setSelectedZona(zona)}
                    className="w-full p-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg text-left"
                  >
                    <span className="font-bold text-gray-900 dark:text-gray-100">{zona.name}</span>
                    <span className={`ml-2 px-2 py-1 rounded text-xs font-bold ${getEstadoStyles(zona.estado)}`}>
                      {getEstadoLabel(zona.estado)}
                    </span>
                    <p className="text-xs text-gray-500 dark:text-gray-300 mt-1 flex flex-wrap gap-x-2">
                      <span>🚶 {dist.walking}</span>
                      <span>🚗 {dist.driving}</span>
                      <span>⏱️ {zona.estimated_wait} min</span>
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

  if (modo === 'guiar') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/')} />

        <div className="bg-danger text-white px-4 py-3">
          <h2 className="font-bold text-lg">👉 Zona gastronómica saturada</h2>
        </div>

        <div className="flex-1 p-4 space-y-4">
          {principal && (() => {
            const dist = getDistancias(principal.lat ?? 0, principal.lng ?? 0, userLocation, principal.distancia_min ?? 5)
            return (
              <button onClick={() => setSelectedZona(principal)} className="w-full">
                <div className="bg-primary text-white p-6 rounded-xl text-left shadow-lg">
                  <p className="text-lg font-bold">👉 Dirigite ahora a {principal.name}</p>
                  <p className="text-sm opacity-90 mt-2">📍 {principal.referencia}</p>
                  <p className="text-sm opacity-90 flex gap-3">
                    <span>🚶 {dist.walking}</span>
                    <span>🚗 {dist.driving}</span>
                  </p>
                  <p className="text-sm opacity-90">⏱️ Espera: {principal.estimated_wait} min</p>
                  {principal.estado === 'alto' && (
                    <p className="text-xs opacity-75 mt-2">⚠️ Últimos lugares</p>
                  )}
                </div>
              </button>
            )
          })()}

          {alternativa && principal?.estado !== 'colapsado' && (() => {
            const dist = getDistancias(alternativa.lat ?? 0, alternativa.lng ?? 0, userLocation, alternativa.distancia_min ?? 5)
            return (
              <button onClick={() => setSelectedZona(alternativa)} className="w-full">
                <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
                  <p className="font-bold text-slate-800 dark:text-slate-100">👉 Si está lleno → {alternativa.name}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">📍 {alternativa.referencia}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-300 flex gap-3">
                    <span>🚶 {dist.walking}</span>
                    <span>🚗 {dist.driving}</span>
                    <span>⏱️ {alternativa.estimated_wait} min</span>
                  </p>
                </div>
              </button>
            )
          })()}

          <p className="text-xs text-slate-400 dark:text-slate-400 text-center">
            {getConfianzaLabel(principal?.confidence ?? 0.5)}
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

  if (modo === 'asistir') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 space-y-4">
          {principal && (() => {
            const dist = getDistancias(principal.lat ?? 0, principal.lng ?? 0, userLocation, principal.distancia_min ?? 5)
            return (
              <button onClick={() => setSelectedZona(principal)} className="w-full">
                <div className="bg-white dark:bg-slate-800 border-l-4 border-primary p-4 rounded-xl text-left shadow-md">
                  <p className="font-bold text-slate-800 dark:text-slate-100 text-lg">👉 Mejor opción ahora: {principal.name}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-300 mt-2">📍 {principal.referencia}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-300 flex gap-3">
                    <span>🚶 {dist.walking}</span>
                    <span>🚗 {dist.driving}</span>
                    <span>⏱️ {principal.estimated_wait} min</span>
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-300 mt-2">{formatUpdatedAt(Date.now())}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-300 mt-1">{getConfianzaLabel(principal.confidence)}</p>
                </div>
              </button>
            )
          })()}

          {alternativa && (() => {
            const dist = getDistancias(alternativa.lat ?? 0, alternativa.lng ?? 0, userLocation, alternativa.distancia_min ?? 5)
            return (
              <button onClick={() => setSelectedZona(alternativa)} className="w-full">
                <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
                  <p className="font-bold text-slate-800 dark:text-slate-100">Alternativa: {alternativa.name}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">📍 {alternativa.referencia}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-300 flex gap-3">
                    <span>🚶 {dist.walking}</span>
                    <span>🚗 {dist.driving}</span>
                    <span>⏱️ {alternativa.estimated_wait} min</span>
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
            <p className="text-[10px] text-blue-500 font-semibold mb-3">📡 Ubicación GPS activa</p>
          )}
          <div className="space-y-3">
            {zonas.slice(0, 3).map((zona) => {
              const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min ?? 5)
              return (
                <button
                  key={zona.zone_id}
                  onClick={() => setSelectedZona(zona)}
                  className="w-full p-4 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-left hover:border-primary dark:hover:border-primary/70 transition-colors"
                >
                  <div className="flex justify-between items-center">
                    <span className="font-bold mr-2 text-gray-900 dark:text-gray-100">{zona.name}</span>
                    <span className={`px-2 py-1 rounded text-xs font-bold whitespace-nowrap shrink-0 ${getEstadoStyles(zona.estado)}`}>
                      {getEstadoLabel(zona.estado)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">📍 {zona.referencia}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-300 flex flex-wrap gap-x-3 gap-y-0.5">
                    <span>🚶 {dist.walking}</span>
                    <span>🚗 {dist.driving}</span>
                    <span>⏱️ {zona.estimated_wait} min espera</span>
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-300 mt-1">{formatUpdatedAt(Date.now())}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-300 mt-1">{getConfianzaLabel(zona.confidence)}</p>
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
