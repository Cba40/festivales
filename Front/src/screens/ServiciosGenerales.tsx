import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { InteractiveMap } from '@/components/InteractiveMap'
import { X, Bath, Droplets, Armchair, HeartPulse, Info, Map as MapIcon } from 'lucide-react'
import { formatUpdatedAt } from '@/utils/formatTime'
import { getDistancias } from '@/utils/geo'
import { useBathroomRecommendations, type ZonaSanitaryItem } from '@/services/bathroomProduct'
import { useRestRecommendations, type ZonaRestItem } from '@/services/restProduct'
import { useHealthRecommendations, type ZonaSaludItem } from '@/services/healthProduct'
import { useHydrationRecommendations, type ZonaHidratacionItem } from '@/services/hydrationProduct'

const opciones = [
  { icon: Bath, label: 'Baños', subtipo: 'banos', colorScheme: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' },
  { icon: Droplets, label: 'Agua', subtipo: 'hidratacion', colorScheme: 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-400' },
  { icon: Armchair, label: 'Descanso', subtipo: 'descanso', colorScheme: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400' },
  { icon: HeartPulse, label: 'Salud', subtipo: 'salud', colorScheme: 'bg-danger/10 dark:bg-danger/20 text-danger' }
]

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

const ServiciosGenerales = () => {
  const navigate = useNavigate()
  const [subtipoActivo, setSubtipoActivo] = useState<string | null>(null)
  const [userLocation] = useState<[number, number] | null>(null)
  const [selectedZona, setSelectedZona] = useState<ZonaSanitaryItem | null>(null)
  const [selectedZonaRest, setSelectedZonaRest] = useState<ZonaRestItem | null>(null)
  const [selectedZonaSalud, setSelectedZonaSalud] = useState<ZonaSaludItem | null>(null)
  const [selectedZonaHidratacion, setSelectedZonaHidratacion] = useState<ZonaHidratacionItem | null>(null)

  const isBanos = subtipoActivo === 'banos'
  const isDescanso = subtipoActivo === 'descanso'
  const isSalud = subtipoActivo === 'salud'
  const isHidratacion = subtipoActivo === 'hidratacion'

  const { data: bathroomData, loading, error, refresh } = useBathroomRecommendations()
  const {
    data: restData,
    loading: restLoading,
    error: restError,
    refresh: refreshRest,
  } = useRestRecommendations()
  const {
    data: healthData,
    loading: healthLoading,
    error: healthError,
    refresh: refreshHealth,
  } = useHealthRecommendations()
  const {
    data: hydrationData,
    loading: hydrationLoading,
    error: hydrationError,
    refresh: refreshHydration,
  } = useHydrationRecommendations()

  useEffect(() => {
    if (isBanos) refresh()
  }, [isBanos, refresh])

  useEffect(() => {
    if (isDescanso) refreshRest()
  }, [isDescanso, refreshRest])

  useEffect(() => {
    if (isSalud) refreshHealth()
  }, [isSalud, refreshHealth])

  useEffect(() => {
    if (isHidratacion) refreshHydration()
  }, [isHidratacion, refreshHydration])

  const bathrooms = bathroomData?.zonas ?? []
  const modoBathroom = bathroomData?.mode ?? 'informar'

  const restItems = restData?.zonas ?? []
  const modoRest = restData?.mode ?? 'informar'

  const healthItems = healthData?.zonas ?? []
  const modoHealth = healthData?.mode ?? 'informar'

  const hydrationItems = hydrationData?.zonas ?? []
  const modoHydration = hydrationData?.mode ?? 'informar'

  const abrirMapaRest = (zona: ZonaRestItem) => {
    if (zona.lat && zona.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${zona.lat},${zona.lng}`,
        '_blank'
      )
    }
    setSelectedZonaRest(null)
  }

  const renderBottomSheetRest = selectedZonaRest && (
    <>
      <div
        className="fixed inset-0 bg-black/50 z-[9999]"
        onClick={() => setSelectedZonaRest(null)}
      />
      <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl">
        <div
          className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
          onClick={() => setSelectedZonaRest(null)}
        />
        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
          {selectedZonaRest.name}
        </h3>
        <div className="space-y-2 mb-4 text-sm text-slate-600 dark:text-slate-300">
          <p>📍 {selectedZonaRest.referencia}</p>
          {(() => {
            const dist = getDistancias(selectedZonaRest.lat ?? 0, selectedZonaRest.lng ?? 0, userLocation, selectedZonaRest.distancia_min ?? 5)
            return (
              <>
                <p className="flex items-center gap-1.5">🚶 <span>Tiempo caminando:</span> <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span></p>
                <p className="flex items-center gap-1.5">🚗 <span>Tiempo en auto:</span> <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span></p>
              </>
            )
          })()}
          <p className="text-sm text-slate-600 dark:text-slate-300">
            ⏱️ Espera: {selectedZonaRest.estimated_wait} min
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {formatUpdatedAt(restData?.timestamp ?? Date.now())}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {getConfianzaLabel(selectedZonaRest.confidence)}
          </p>
        </div>
        <button
          onClick={() => abrirMapaRest(selectedZonaRest)}
          className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2"
        >
          <MapIcon size={18} />
          Iniciar ruta
        </button>
        <button
          onClick={() => setSelectedZonaRest(null)}
          className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold flex items-center justify-center gap-2"
        >
          <X size={16} /> Cerrar
        </button>
      </div>
    </>
  )

  const abrirMapaSalud = (zona: ZonaSaludItem) => {
    if (zona.lat && zona.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${zona.lat},${zona.lng}`,
        '_blank'
      )
    }
    setSelectedZonaSalud(null)
  }

  const renderBottomSheetSalud = selectedZonaSalud && (
    <>
      <div
        className="fixed inset-0 bg-black/50 z-[9999]"
        onClick={() => setSelectedZonaSalud(null)}
      />
      <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl">
        <div
          className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
          onClick={() => setSelectedZonaSalud(null)}
        />
        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
          {selectedZonaSalud.name}
        </h3>
        <div className="space-y-2 mb-4 text-sm text-slate-600 dark:text-slate-300">
          <p>📍 {selectedZonaSalud.referencia}</p>
          {(() => {
            const dist = getDistancias(selectedZonaSalud.lat ?? 0, selectedZonaSalud.lng ?? 0, userLocation, selectedZonaSalud.distancia_min ?? 5)
            return (
              <>
                <p className="flex items-center gap-1.5">🚶 <span>Tiempo caminando:</span> <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span></p>
                <p className="flex items-center gap-1.5">🚗 <span>Tiempo en auto:</span> <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span></p>
              </>
            )
          })()}
          <p className="text-sm text-slate-600 dark:text-slate-300">
            ⏱️ Espera: {selectedZonaSalud.estimated_wait} min
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {formatUpdatedAt(healthData?.timestamp ?? Date.now())}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {getConfianzaLabel(selectedZonaSalud.confidence)}
          </p>
        </div>
        <button
          onClick={() => abrirMapaSalud(selectedZonaSalud)}
          className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2"
        >
          <MapIcon size={18} />
          Iniciar ruta
        </button>
        <button
          onClick={() => setSelectedZonaSalud(null)}
          className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold flex items-center justify-center gap-2"
        >
          <X size={16} /> Cerrar
        </button>
      </div>
    </>
  )

  const abrirMapaHidratacion = (zona: ZonaHidratacionItem) => {
    if (zona.lat && zona.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${zona.lat},${zona.lng}`,
        '_blank'
      )
    }
    setSelectedZonaHidratacion(null)
  }

  const renderBottomSheetHidratacion = selectedZonaHidratacion && (
    <>
      <div
        className="fixed inset-0 bg-black/50 z-[9999]"
        onClick={() => setSelectedZonaHidratacion(null)}
      />
      <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl">
        <div
          className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
          onClick={() => setSelectedZonaHidratacion(null)}
        />
        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
          {selectedZonaHidratacion.name}
        </h3>
        <div className="space-y-2 mb-4 text-sm text-slate-600 dark:text-slate-300">
          <p>📍 {selectedZonaHidratacion.referencia}</p>
          {(() => {
            const dist = getDistancias(selectedZonaHidratacion.lat ?? 0, selectedZonaHidratacion.lng ?? 0, userLocation, selectedZonaHidratacion.distancia_min ?? 5)
            return (
              <>
                <p className="flex items-center gap-1.5">🚶 <span>Tiempo caminando:</span> <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span></p>
                <p className="flex items-center gap-1.5">🚗 <span>Tiempo en auto:</span> <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span></p>
              </>
            )
          })()}
          <p className="text-sm text-slate-600 dark:text-slate-300">
            ⏱️ Espera: {selectedZonaHidratacion.estimated_wait} min
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {formatUpdatedAt(hydrationData?.timestamp ?? Date.now())}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {getConfianzaLabel(selectedZonaHidratacion.confidence)}
          </p>
        </div>
        <button
          onClick={() => abrirMapaHidratacion(selectedZonaHidratacion)}
          className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2"
        >
          <MapIcon size={18} />
          Iniciar ruta
        </button>
        <button
          onClick={() => setSelectedZonaHidratacion(null)}
          className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold flex items-center justify-center gap-2"
        >
          <X size={16} /> Cerrar
        </button>
      </div>
    </>
  )

  const abrirMapa = (zona: ZonaSanitaryItem) => {
    if (zona.lat && zona.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${zona.lat},${zona.lng}`,
        '_blank'
      )
    }
    setSelectedZona(null)
  }

  const renderBottomSheetBathroom = selectedZona && (
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
            {formatUpdatedAt(bathroomData?.timestamp ?? Date.now())}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {getConfianzaLabel(selectedZona.confidence)}
          </p>
        </div>

        <button
          onClick={() => abrirMapa(selectedZona)}
          className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2"
        >
          <MapIcon size={20} />
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

  if (!subtipoActivo) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Más servicios" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4">
          <div className="grid grid-cols-2 gap-3">
            {opciones.map(op => {
              const Icon = op.icon
              return (
                <button
                  key={op.subtipo}
                  onClick={() => setSubtipoActivo(op.subtipo)}
                  className="bg-white dark:bg-slate-800 p-5 rounded-xl shadow-md hover:shadow-lg transition-all active:scale-95 flex flex-col items-center gap-2"
                >
                  <div className={`w-12 h-12 rounded-xl ${op.colorScheme} flex items-center justify-center`}>
                    <Icon size={24} />
                  </div>
                  <p className="font-bold text-sm text-slate-800 dark:text-slate-100">{op.label}</p>
                </button>
              )
            })}
          </div>
        </div>
      </div>
    )
  }

  if (isBanos && loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Baños" showBack onBack={() => setSubtipoActivo(null)} />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-500">Cargando recomendaciones...</p>
        </div>
      </div>
    )
  }

  if (isBanos && error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Baños" showBack onBack={() => setSubtipoActivo(null)} />
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

  if (isBanos && modoBathroom === 'sin_solucion') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Baños" showBack onBack={() => setSubtipoActivo(null)} />

        <div className="flex-1 p-4 space-y-4">
          <div className="bg-danger text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">🚧 Todos los baños están colapsados</p>
            <p className="text-sm mt-2 opacity-90">Tiempos de espera y acceso elevados</p>
          </div>

          {bathrooms.length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-red-500 text-center">
                ⚠️ Disponibilidad muy baja — podés no encontrar lugar
              </p>
              {bathrooms.slice(0, 2).map(zona => {
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

        {renderBottomSheetBathroom}
      </div>
    )
  }

  if (isBanos) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Baños" showBack onBack={() => setSubtipoActivo(null)} />

        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          <InteractiveMap
            puntos={bathrooms
              .filter(z => z.lat && z.lng)
              .map(z => ({
                id: z.zone_id,
                nombre: z.name,
                lat: z.lat!,
                lng: z.lng!,
                referencia: z.referencia,
                tipo: 'banos',
                originalData: z
              }))}
            onSelectPunto={(p) => setSelectedZona(p as ZonaSanitaryItem)}
            onUserLocationUpdate={() => {}}
          />

          <div className="space-y-2 pb-6">
            <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 flex justify-between">
              <span>🚻 {bathrooms.length} baños disponibles</span>
              {userLocation && <span className="text-blue-500 text-[10px] font-semibold">📡 Ubicación GPS activa</span>}
            </p>
            {bathrooms.map(zona => {
              const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min ?? 5)
              return (
                <button
                  key={zona.zone_id}
                  onClick={() => setSelectedZona(zona)}
                  className="w-full text-left bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors group shadow-sm flex items-start gap-2"
                >
                  <span className="text-lg mt-0.5">🚻</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center">
                      <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">
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
                      <span className="opacity-50">·</span>
                      <span className={zona.confidence >= 0.7 ? 'text-green-600' : zona.confidence >= 0.4 ? 'text-yellow-600' : 'text-red-600'}>
                        {getConfianzaLabel(zona.confidence)}
                      </span>
                    </p>
                  </div>
                  <Info size={16} className="text-slate-400 flex-shrink-0" />
                </button>
              )
            })}
          </div>
        </div>

        {renderBottomSheetBathroom}
      </div>
    )
  }

  if (isDescanso && restLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Descanso" showBack onBack={() => setSubtipoActivo(null)} />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-500">Cargando recomendaciones...</p>
        </div>
      </div>
    )
  }

  if (isDescanso && restError) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Descanso" showBack onBack={() => setSubtipoActivo(null)} />
        <div className="flex-1 p-4 flex flex-col items-center justify-center space-y-4">
          <p className="text-danger font-bold">Error al cargar</p>
          <p className="text-sm text-slate-500 text-center">{restError}</p>
          <button
            onClick={refreshRest}
            className="bg-primary text-white px-6 py-2 rounded-lg font-bold"
          >
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  if (isDescanso && modoRest === 'sin_solucion') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Descanso" showBack onBack={() => setSubtipoActivo(null)} />

        <div className="flex-1 p-4 space-y-4">
          <div className="bg-danger text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">🪑 Todas las zonas de descanso están colapsadas</p>
            <p className="text-sm mt-2 opacity-90">Tiempos de espera y acceso elevados</p>
          </div>

          {restItems.length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-red-500 text-center">
                ⚠️ Disponibilidad muy baja — podés no encontrar lugar
              </p>
              {restItems.slice(0, 2).map(zona => {
                const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min ?? 5)
                return (
                  <button
                    key={zona.zone_id}
                    onClick={() => setSelectedZonaRest(zona)}
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

        {renderBottomSheetRest}
      </div>
    )
  }

  if (isDescanso) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Descanso" showBack onBack={() => setSubtipoActivo(null)} />

        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          <InteractiveMap
            puntos={restItems
              .filter(z => z.lat && z.lng)
              .map(z => ({
                id: z.zone_id,
                nombre: z.name,
                lat: z.lat!,
                lng: z.lng!,
                referencia: z.referencia,
                tipo: 'descanso',
                originalData: z
              }))}
            onSelectPunto={(p) => setSelectedZonaRest(p as ZonaRestItem)}
            onUserLocationUpdate={() => {}}
          />

          <div className="space-y-2 pb-6">
            <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 flex justify-between">
              <span>🪑 {restItems.length} zonas de descanso disponibles</span>
              {userLocation && <span className="text-blue-500 text-[10px] font-semibold">📡 Ubicación GPS activa</span>}
            </p>
            {restItems.map(zona => {
              const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min ?? 5)
              return (
                <button
                  key={zona.zone_id}
                  onClick={() => setSelectedZonaRest(zona)}
                  className="w-full text-left bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors group shadow-sm flex items-start gap-2"
                >
                  <span className="text-lg mt-0.5">🪑</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center">
                      <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">
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
                      <span className="opacity-50">·</span>
                      <span className={zona.confidence >= 0.7 ? 'text-green-600' : zona.confidence >= 0.4 ? 'text-yellow-600' : 'text-red-600'}>
                        {getConfianzaLabel(zona.confidence)}
                      </span>
                    </p>
                  </div>
                  <Info size={16} className="text-slate-400 flex-shrink-0" />
                </button>
              )
            })}
          </div>
        </div>

        {renderBottomSheetRest}
      </div>
    )
  }

  if (isSalud && healthLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Salud" showBack onBack={() => setSubtipoActivo(null)} />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-500">Cargando recomendaciones...</p>
        </div>
      </div>
    )
  }

  if (isSalud && healthError) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Salud" showBack onBack={() => setSubtipoActivo(null)} />
        <div className="flex-1 p-4 flex flex-col items-center justify-center space-y-4">
          <p className="text-danger font-bold">Error al cargar</p>
          <p className="text-sm text-slate-500 text-center">{healthError}</p>
          <button
            onClick={refreshHealth}
            className="bg-primary text-white px-6 py-2 rounded-lg font-bold"
          >
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  if (isSalud && modoHealth === 'sin_solucion') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Salud" showBack onBack={() => setSubtipoActivo(null)} />

        <div className="flex-1 p-4 space-y-4">
          <div className="bg-danger text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">🏥 Todas las zonas de salud están colapsadas</p>
            <p className="text-sm mt-2 opacity-90">Tiempos de espera y acceso elevados</p>
          </div>

          {healthItems.length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-red-500 text-center">
                ⚠️ Disponibilidad muy baja — podés no encontrar lugar
              </p>
              {healthItems.slice(0, 2).map(zona => {
                const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min ?? 5)
                return (
                  <button
                    key={zona.zone_id}
                    onClick={() => setSelectedZonaSalud(zona)}
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

        {renderBottomSheetSalud}
      </div>
    )
  }

  if (isSalud) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Salud" showBack onBack={() => setSubtipoActivo(null)} />

        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          <InteractiveMap
            puntos={healthItems
              .filter(z => z.lat && z.lng)
              .map(z => ({
                id: z.zone_id,
                nombre: z.name,
                lat: z.lat!,
                lng: z.lng!,
                referencia: z.referencia,
                tipo: 'salud',
                originalData: z
              }))}
            onSelectPunto={(p) => setSelectedZonaSalud(p as ZonaSaludItem)}
            onUserLocationUpdate={() => {}}
          />

          <div className="space-y-2 pb-6">
            <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 flex justify-between">
              <span>🏥 {healthItems.length} zonas de salud disponibles</span>
              {userLocation && <span className="text-blue-500 text-[10px] font-semibold">📡 Ubicación GPS activa</span>}
            </p>
            {healthItems.map(zona => {
              const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min ?? 5)
              return (
                <button
                  key={zona.zone_id}
                  onClick={() => setSelectedZonaSalud(zona)}
                  className="w-full text-left bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors group shadow-sm flex items-start gap-2"
                >
                  <span className="text-lg mt-0.5">🏥</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center">
                      <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">
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
                      <span className="opacity-50">·</span>
                      <span className={zona.confidence >= 0.7 ? 'text-green-600' : zona.confidence >= 0.4 ? 'text-yellow-600' : 'text-red-600'}>
                        {getConfianzaLabel(zona.confidence)}
                      </span>
                    </p>
                  </div>
                  <Info size={16} className="text-slate-400 flex-shrink-0" />
                </button>
              )
            })}
          </div>
        </div>

        {renderBottomSheetSalud}
      </div>
    )
  }

  if (isHidratacion && hydrationLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Agua" showBack onBack={() => setSubtipoActivo(null)} />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-500">Cargando recomendaciones...</p>
        </div>
      </div>
    )
  }

  if (isHidratacion && hydrationError) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Agua" showBack onBack={() => setSubtipoActivo(null)} />
        <div className="flex-1 p-4 flex flex-col items-center justify-center space-y-4">
          <p className="text-danger font-bold">Error al cargar</p>
          <p className="text-sm text-slate-500 text-center">{hydrationError}</p>
          <button
            onClick={refreshHydration}
            className="bg-primary text-white px-6 py-2 rounded-lg font-bold"
          >
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  if (isHidratacion && modoHydration === 'sin_solucion') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Agua" showBack onBack={() => setSubtipoActivo(null)} />

        <div className="flex-1 p-4 space-y-4">
          <div className="bg-danger text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">💧 Todos los puntos de hidratación están colapsados</p>
            <p className="text-sm mt-2 opacity-90">Tiempos de espera y acceso elevados</p>
          </div>

          {hydrationItems.length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-red-500 text-center">
                ⚠️ Disponibilidad muy baja — podés no encontrar lugar
              </p>
              {hydrationItems.slice(0, 2).map(zona => {
                const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min ?? 5)
                return (
                  <button
                    key={zona.zone_id}
                    onClick={() => setSelectedZonaHidratacion(zona)}
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

        {renderBottomSheetHidratacion}
      </div>
    )
  }

  if (isHidratacion) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Agua" showBack onBack={() => setSubtipoActivo(null)} />

        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          <InteractiveMap
            puntos={hydrationItems
              .filter(z => z.lat && z.lng)
              .map(z => ({
                id: z.zone_id,
                nombre: z.name,
                lat: z.lat!,
                lng: z.lng!,
                referencia: z.referencia,
                tipo: 'hidratacion',
                originalData: z
              }))}
            onSelectPunto={(p) => setSelectedZonaHidratacion(p as ZonaHidratacionItem)}
            onUserLocationUpdate={() => {}}
          />

          <div className="space-y-2 pb-6">
            <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 flex justify-between">
              <span>💧 {hydrationItems.length} puntos de hidratación disponibles</span>
              {userLocation && <span className="text-blue-500 text-[10px] font-semibold">📡 Ubicación GPS activa</span>}
            </p>
            {hydrationItems.map(zona => {
              const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min ?? 5)
              return (
                <button
                  key={zona.zone_id}
                  onClick={() => setSelectedZonaHidratacion(zona)}
                  className="w-full text-left bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors group shadow-sm flex items-start gap-2"
                >
                  <span className="text-lg mt-0.5">💧</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center">
                      <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">
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
                      <span className="opacity-50">·</span>
                      <span className={zona.confidence >= 0.7 ? 'text-green-600' : zona.confidence >= 0.4 ? 'text-yellow-600' : 'text-red-600'}>
                        {getConfianzaLabel(zona.confidence)}
                      </span>
                    </p>
                  </div>
                  <Info size={16} className="text-slate-400 flex-shrink-0" />
                </button>
              )
            })}
          </div>
        </div>

        {renderBottomSheetHidratacion}
      </div>
    )
  }

  return null
}

export default ServiciosGenerales
