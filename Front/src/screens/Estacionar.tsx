import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Map, X } from 'lucide-react'
import { InteractiveMap } from '@/components/InteractiveMap'
import { useAppStore } from '@/core/state/store'
import { useParkingRecommendations, type ZonaEstacionamientoItem } from '@/services/parkingProduct'
import {
  ZonaCardsList,
  getEstadoStyles,
  getEstadoLabel,
  getConfianzaLabel,
  NearestBadge,
} from '@/components/ZonaCardsList'
import { GpsModal } from '@/components/GpsModal'
import { formatUpdatedAt } from '@/utils/formatTime'
import { getDistancias } from '@/utils/geo'

const Estacionar = () => {
  const navigate = useNavigate()
  const { data, loading, error, refresh } = useParkingRecommendations()
  const [selectedZona, setSelectedZona] = useState<ZonaEstacionamientoItem | null>(null)
  const [mostrarGpsModal, setMostrarGpsModal] = useState(true)
  const userLocation = useAppStore(s => s.userLocation)
  const requestLocation = useAppStore(s => s.requestLocation)

  useEffect(() => {
    refresh()
  }, [refresh])

  const zonas = data?.zonas ?? []

  const modo = data?.mode ?? 'informar'

  const principal = zonas[0]
  const alternativa = zonas[1]
  const terceraOpcion = zonas[2]

  const abrirMapa = (zona: ZonaEstacionamientoItem) => {
    if (zona.lat && zona.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${zona.lat},${zona.lng}`,
        '_blank'
      )
    }
    setSelectedZona(null)
  }

  const getTituloZona = (index: number): string => {
    if (index === 0) return '👉 Mejor opción ahora'
    return 'Alternativa'
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
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🚶 Tiempo caminando: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span>
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🚗 Tiempo en auto: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span>
                </p>
              </>
            )
          })()}
          {selectedZona.saturation_level != null && (
            <p className="text-sm text-slate-600 dark:text-slate-300">
              📊 Posibilidad: {Math.round((1 - selectedZona.saturation_level) * 100)}%
            </p>
          )}
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {formatUpdatedAt(data?.timestamp ? Date.parse(data.timestamp) : Date.now())}
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Estacionar" showBack onBack={() => navigate('/')} />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-500">Cargando recomendaciones...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Estacionar" showBack onBack={() => navigate('/')} />
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

  if (modo === 'sin_solucion') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Estacionar" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 space-y-4">
          <div className="bg-danger text-white p-6 rounded-xl text-center">
            {zonas.length > 0 ? (
              <p className="text-xl font-bold">🚧 Disponibilidad muy limitada — podés no encontrar lugar</p>
            ) : (
              <p className="text-xl font-bold">🚧 No hay opciones convenientes para estacionar</p>
            )}
            <p className="text-sm mt-2 opacity-90">Alta demanda en toda la zona</p>
          </div>

          {!userLocation && mostrarGpsModal && (
            <GpsModal
              mensaje="Para mostrarte la opción de estacionamiento más cercana, necesitamos tu ubicación GPS."
              onActivate={() => {
                requestLocation()
                setMostrarGpsModal(false)
              }}
              onClose={() => setMostrarGpsModal(false)}
            />
          )}

          {zonas.length === 0 && (
            <div className="bg-slate-100 dark:bg-slate-700 p-4 rounded-xl space-y-3">
              <button className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform">
                ⏱️ Esperar 20–30 min
              </button>
              <button className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform">
                🚶 Alejarse de esta zona
              </button>
            </div>
          )}

          {zonas.length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-red-500 text-center">
                ⚠️ Disponibilidad muy baja — podés no encontrar lugar
              </p>
              {zonas.slice(0, 3).map((zona, index) => {
                const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min ?? 5)
                return (
                  <button
                    key={zona.zone_id}
                    onClick={() => setSelectedZona(zona)}
                    className="w-full p-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg text-left"
                  >
                    <span className="font-bold text-gray-900 dark:text-gray-100">
                      {index < 2 ? `${getTituloZona(index)}: ${zona.name}` : zona.name}
                    </span>
                    <NearestBadge visible={zona.is_nearest} />
                    <span className={`ml-2 px-2 py-1 rounded text-xs font-bold ${getEstadoStyles(zona.estado)}`}>
                      {getEstadoLabel(zona.estado)}
                    </span>
                    <p className="text-xs text-gray-500 dark:text-gray-300 mt-1 flex flex-wrap gap-x-2">
                      <span>🚗 {dist.driving}</span>
                      {zona.saturation_level != null && <span>📊 {Math.round((1 - zona.saturation_level) * 100)}%</span>}
                    </p>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {renderBottomSheet}
      </div>
    )
  }

  const esTresOpciones = modo === 'guiar' || modo === 'asistir'
  const listaRestante = esTresOpciones ? zonas.slice(3) : zonas.slice(1)

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Estacionar" showBack onBack={() => navigate('/')} />

      {modo === 'guiar' && (
        <div className="bg-danger text-white px-4 py-3">
          <h2 className="font-bold text-lg">👉 Zona actual saturada</h2>
        </div>
      )}

      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {!esTresOpciones && principal && (
          <button
            onClick={() => abrirMapa(principal)}
            className="w-full bg-primary hover:bg-primary-dark text-white p-6 rounded-2xl shadow-lg transition-transform active:scale-95"
          >
            <div className="flex items-center justify-between">
              <div className="text-left flex-1">
                <p className="text-2xl font-bold mb-1">IR AHORA</p>
                <p className="text-lg opacity-90">{principal.name}</p>
                <p className="text-sm opacity-75 mt-1">
                  🚗 {getDistancias(principal.lat ?? 0, principal.lng ?? 0, userLocation, principal.distancia_min ?? 5).driving}
                  {principal.saturation_level != null && ` · 📊 ${Math.round((1 - principal.saturation_level) * 100)}% libre`}
                </p>
              </div>
              <div className="text-4xl">🧭</div>
            </div>
          </button>
        )}

        {esTresOpciones && principal && (
          <button onClick={() => setSelectedZona(principal)} className="w-full">
            <div className={modo === 'guiar'
              ? 'bg-primary text-white p-6 rounded-xl text-left shadow-lg'
              : 'bg-white dark:bg-slate-800 border-l-4 border-primary p-4 rounded-xl text-left shadow-md'}>
              <p className={`font-bold text-lg ${modo === 'asistir' ? 'text-slate-800 dark:text-slate-100' : ''}`}>
                {getTituloZona(0)}: {principal.name}
              </p>
              <p className="text-sm opacity-90 mt-2">📍 {principal.referencia}</p>
              {(() => {
                const dist = getDistancias(principal.lat ?? 0, principal.lng ?? 0, userLocation, principal.distancia_min ?? 5)
                return (
                  <p className="text-sm opacity-90 flex gap-3">
                    <span>🚗 {dist.driving}</span>
                    {principal.saturation_level != null && <span>📊 {Math.round((1 - principal.saturation_level) * 100)}% de posibilidad</span>}
                  </p>
                )
              })()}
              {Math.round((1 - (principal.saturation_level ?? 0)) * 100) < 20 && (
                <p className="text-xs opacity-75 mt-2">⚠️ Disponibilidad limitada</p>
              )}
              {modo === 'asistir' && (
                <>
                  <p className="text-xs text-slate-500 dark:text-slate-300 mt-2">
                    {formatUpdatedAt(data?.timestamp ? Date.parse(data.timestamp) : Date.now())}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-300 mt-1">
                    {getConfianzaLabel(principal.confidence)}
                  </p>
                </>
              )}
            </div>
          </button>
        )}

        {esTresOpciones && alternativa && (
          <button onClick={() => setSelectedZona(alternativa)} className="w-full">
            <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
              <p className="font-bold text-slate-800 dark:text-slate-100">
                {getTituloZona(1)}: {alternativa.name}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                📍 {alternativa.referencia}
              </p>
              {(() => {
                const dist = getDistancias(alternativa.lat ?? 0, alternativa.lng ?? 0, userLocation, alternativa.distancia_min ?? 5)
                return (
                  <p className="text-sm text-slate-600 dark:text-slate-300 flex gap-3">
                    <span>🚗 {dist.driving}</span>
                    {alternativa.saturation_level != null && <span>📊 {Math.round((1 - alternativa.saturation_level) * 100)}% de posibilidad</span>}
                  </p>
                )
              })()}
            </div>
          </button>
        )}

        {esTresOpciones && terceraOpcion && (
          <button onClick={() => setSelectedZona(terceraOpcion)} className="w-full">
            <div className="bg-white dark:bg-slate-800 border-2 border-blue-400 dark:border-blue-500 p-4 rounded-xl text-left">
              <p className="font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                <span>{terceraOpcion.name}</span>
                <NearestBadge visible={terceraOpcion.is_nearest} />
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                📍 {terceraOpcion.referencia}
              </p>
              {(() => {
                const dist = getDistancias(terceraOpcion.lat ?? 0, terceraOpcion.lng ?? 0, userLocation, terceraOpcion.distancia_min ?? 5)
                return (
                  <p className="text-sm text-slate-600 dark:text-slate-300 flex gap-3">
                    <span>🚗 {dist.driving}</span>
                    {terceraOpcion.saturation_level != null && <span>📊 {Math.round((1 - terceraOpcion.saturation_level) * 100)}% de posibilidad</span>}
                  </p>
                )
              })()}
            </div>
          </button>
        )}

        <InteractiveMap
          puntos={zonas
            .filter(z => z.lat && z.lng)
            .map(z => ({
              id: z.zone_id,
              nombre: z.name,
              lat: z.lat!,
              lng: z.lng!,
              referencia: z.referencia,
              tipo: 'estacionamiento',
              originalData: z
            }))}
          onSelectPunto={(p) => setSelectedZona(p as ZonaEstacionamientoItem)}
          onUserLocationUpdate={() => {}}
        />

        {listaRestante.length > 0 && (
          <ZonaCardsList
            items={listaRestante}
            icon="🚗"
            label="zonas de estacionamiento disponibles"
            userLocation={userLocation}
            onSelect={(z) => setSelectedZona(z)}
          />
        )}

        {esTresOpciones && (
          <p className="text-xs text-slate-400 dark:text-slate-400 text-center pb-16">
            {getConfianzaLabel(principal?.confidence)}
          </p>
        )}
      </div>

      {!userLocation && mostrarGpsModal && (
        <GpsModal
          mensaje="Para mostrarte la opción de estacionamiento más cercana, necesitamos tu ubicación GPS."
          onActivate={() => {
            requestLocation()
            setMostrarGpsModal(false)
          }}
          onClose={() => setMostrarGpsModal(false)}
        />
      )}

      {renderBottomSheet}
    </div>
  )
}

export default Estacionar
