import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { InteractiveMap } from '@/components/InteractiveMap'
import { X, Bath, Droplets, Armchair, HeartPulse, Info, Map as MapIcon } from 'lucide-react'
import { mapZonesToServiciosMapa, type PuntoServicioMapa } from '@/data/mappers'
import { useAppStore } from '@/core/state/store'
import { formatUpdatedAt } from '@/utils/formatTime'
import { getDistancias } from '@/utils/geo'
import { useBathroomRecommendations, type ZonaSanitaryItem } from '@/services/bathroomProduct'

const opciones = [
  { icon: Bath, label: 'Baños', subtipo: 'banos', colorScheme: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' },
  { icon: Droplets, label: 'Agua', subtipo: 'hidratacion', colorScheme: 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-400' },
  { icon: Armchair, label: 'Descanso', subtipo: 'descanso', colorScheme: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400' },
  { icon: HeartPulse, label: 'Salud', subtipo: 'salud', colorScheme: 'bg-danger/10 dark:bg-danger/20 text-danger' }
]

const getEmoji = (tipo: string) => {
  switch (tipo) {
    case 'banos': return '🚻'
    case 'hidratacion': return '💧'
    case 'descanso': return '🪑'
    case 'salud': return '🏥'
    default: return '📍'
  }
}

const URBAN_FACTOR = 1.3

const haversine = (lat1: number, lng1: number, lat2: number, lng2: number): number => {
  const R = 6371
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLng = ((lng2 - lng1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

const getDistanciasLocal = (puntoLat: number, puntoLng: number, userLoc: [number, number] | null, fallbackMin: number) => {
  if (!userLoc || !puntoLat || !puntoLng) {
    return {
      walking: `${fallbackMin} min`,
      driving: `${Math.max(1, Math.round(fallbackMin / 3))} min`
    }
  }

  const [userLat, userLng] = userLoc
  const km = haversine(userLat, userLng, puntoLat, puntoLng)

  const kmWalking = km * URBAN_FACTOR
  const minWalking = Math.round((kmWalking / 5) * 60)
  const walkingStr = minWalking < 1 ? '< 1 min' : `${minWalking} min`

  const kmDriving = km * 1.5
  const minDriving = Math.round((kmDriving / 25) * 60)
  const drivingStr = minDriving < 1 ? '< 1 min' : `${minDriving} min`

  return { walking: walkingStr, driving: drivingStr }
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

const getConfianzaLabel = (confidence: number): string => {
  if (confidence >= 0.7) return '✅ Alta probabilidad'
  if (confidence >= 0.4) return '⚠️ Últimos lugares'
  return '❗ Disponibilidad incierta'
}

const ServiciosGenerales = () => {
  const navigate = useNavigate()
  const zones = useAppStore(s => s.zones)
  const [selected, setSelected] = useState<PuntoServicioMapa | null>(null)
  const [subtipoActivo, setSubtipoActivo] = useState<string | null>(null)
  const [userLocation, setUserLocation] = useState<[number, number] | null>(null)
  const [selectedZona, setSelectedZona] = useState<ZonaSanitaryItem | null>(null)

  const isBanos = subtipoActivo === 'banos'

  const { data: bathroomData, loading, error, refresh } = useBathroomRecommendations()

  useEffect(() => {
    if (isBanos) refresh()
  }, [isBanos, refresh])

  const bathrooms = bathroomData?.zonas ?? []
  const modoBathroom = bathroomData?.mode ?? 'informar'

  const todosPuntos = useMemo(() => mapZonesToServiciosMapa(zones), [zones])
  const puntos = (!isBanos && subtipoActivo)
    ? todosPuntos.filter(p => p.tipo === subtipoActivo)
    : []

  const puntosOrdenados = useMemo(() => {
    if (!puntos.length) return []
    return [...puntos].sort((a, b) => {
      if (userLocation && a.lat && a.lng && b.lat && b.lng) {
        const distA = haversine(userLocation[0], userLocation[1], a.lat, a.lng)
        const distB = haversine(userLocation[0], userLocation[1], b.lat, b.lng)
        return distA - distB
      }
      return a.distancia - b.distancia
    })
  }, [puntos, userLocation])

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

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title={opciones.find(o => o.subtipo === subtipoActivo)?.label || 'Servicios'} showBack onBack={() => setSubtipoActivo(null)} />

      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        <InteractiveMap
          puntos={puntos}
          onSelectPunto={setSelected}
          onUserLocationUpdate={setUserLocation}
        />

        <div className="space-y-2 pb-6">
          <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 flex justify-between">
            <span>📍 {puntosOrdenados.length} puntos disponibles</span>
            {userLocation && <span className="text-blue-500 text-[10px] font-semibold">📡 Ubicación GPS activa</span>}
          </p>
          {puntosOrdenados.map(punto => {
            const dist = getDistanciasLocal(punto.lat, punto.lng, userLocation, punto.distancia)
            return (
              <button
                key={punto.id}
                onClick={() => setSelected(punto)}
                className="w-full text-left bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors group shadow-sm flex items-start gap-2"
              >
                <span className="text-lg mt-0.5">{getEmoji(punto.tipo)}</span>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                    {punto.nombre}
                  </p>
                  <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 flex flex-wrap gap-x-2 gap-y-0.5 items-center">
                    <span>🚶 {dist.walking}</span>
                    <span className="opacity-50">·</span>
                    <span>🚗 {dist.driving}</span>
                    <span className="opacity-50">·</span>
                    <span className="truncate">{punto.referencia}</span>
                  </p>
                </div>
                <Info size={16} className="text-slate-400 flex-shrink-0" />
              </button>
            )
          })}
          {puntosOrdenados.length === 0 && (
            <p className="text-sm text-slate-500 dark:text-slate-400 italic text-center py-4">
              No hay puntos cargados de este servicio actualmente.
            </p>
          )}
        </div>
      </div>

      {selected && (
        <>
          <div className="fixed inset-0 bg-black/50 z-[9999]" onClick={() => setSelected(null)} />
          <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl">
            <div className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer" onClick={() => setSelected(null)} />
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">{selected.nombre}</h3>

            {(() => {
              const dist = getDistanciasLocal(selected.lat, selected.lng, userLocation, selected.distancia)
              return (
                <div className="space-y-2 mb-4 text-sm text-slate-600 dark:text-slate-300">
                  <p>📍 {selected.referencia}</p>
                  <p className="flex items-center gap-1.5">🚶 <span>Tiempo caminando:</span> <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span></p>
                  <p className="flex items-center gap-1.5">🚗 <span>Tiempo en auto:</span> <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span></p>
                  <p className="text-xs text-slate-500 dark:text-slate-300 pt-1 border-t border-slate-100 dark:border-slate-700/50 mt-2">
                    Actualizado: {formatUpdatedAt(selected.updatedAt)}
                  </p>
                </div>
              )
            })()}

            {selected.lat !== 0 && selected.lng !== 0 && (
              <a
                href={`https://www.google.com/maps/dir/?api=1&destination=${selected.lat},${selected.lng}`}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full flex items-center justify-center gap-2 bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 text-sm"
              >
                <MapIcon size={18} />
                Iniciar ruta
              </a>
            )}

            <button
              onClick={() => setSelected(null)}
              className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold flex items-center justify-center gap-2"
            >
              <X size={16} /> Cerrar
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default ServiciosGenerales
