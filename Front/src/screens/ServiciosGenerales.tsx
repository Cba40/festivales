import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { InteractiveMap } from '@/components/InteractiveMap'
import { X, Bath, Droplets, Armchair, HeartPulse, Info, Map as MapIcon } from 'lucide-react'
import { mapZonesToServiciosMapa, type PuntoServicioMapa } from '@/data/mappers'
import { useAppStore } from '@/core/state/store'
import { formatUpdatedAt } from '@/utils/formatTime'

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

// Lógica de cálculo geográfico Haversine
const URBAN_FACTOR = 1.3

const haversine = (lat1: number, lng1: number, lat2: number, lng2: number): number => {
  const R = 6371 // Radio de la Tierra en km
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLng = ((lng2 - lng1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

const getDistancias = (puntoLat: number, puntoLng: number, userLoc: [number, number] | null, fallbackMin: number) => {
  if (!userLoc || !puntoLat || !puntoLng) {
    return {
      walking: `${fallbackMin} min`,
      driving: `${Math.max(1, Math.round(fallbackMin / 3))} min`
    }
  }

  const [userLat, userLng] = userLoc
  const km = haversine(userLat, userLng, puntoLat, puntoLng)
  
  // Caminando: ~5 km/h promedio en entorno urbano/congestionado
  const kmWalking = km * URBAN_FACTOR
  const minWalking = Math.round((kmWalking / 5) * 60)
  const walkingStr = minWalking < 1 ? '< 1 min' : `${minWalking} min`
  
  // En auto: ~25 km/h promedio en zona del festival
  const kmDriving = km * 1.5
  const minDriving = Math.round((kmDriving / 25) * 60)
  const drivingStr = minDriving < 1 ? '< 1 min' : `${minDriving} min`
  
  return { walking: walkingStr, driving: drivingStr }
}

const ServiciosGenerales = () => {
  const navigate = useNavigate()
  const zones = useAppStore(s => s.zones)
  const [selected, setSelected] = useState<PuntoServicioMapa | null>(null)
  const [subtipoActivo, setSubtipoActivo] = useState<string | null>(null)
  const [userLocation, setUserLocation] = useState<[number, number] | null>(null)

  const todosPuntos = useMemo(() => mapZonesToServiciosMapa(zones), [zones])
  const puntos = subtipoActivo ? todosPuntos.filter(p => p.tipo === subtipoActivo) : []

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

  const seleccionar = (subtipo: string) => {
    setSubtipoActivo(subtipo)
  }

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
                  onClick={() => seleccionar(op.subtipo)}
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

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title={opciones.find(o => o.subtipo === subtipoActivo)?.label || 'Servicios'} showBack onBack={() => setSubtipoActivo(null)} />

      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {/* Renderiza el mapa Leaflet real y captura ubicación */}
        <InteractiveMap 
          puntos={puntos} 
          onSelectPunto={setSelected} 
          onUserLocationUpdate={setUserLocation} 
        />

        {/* Lista de referencia rápida para el usuario */}
        <div className="space-y-2 pb-6">
          <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 flex justify-between">
            <span>📍 {puntosOrdenados.length} puntos disponibles</span>
            {userLocation && <span className="text-blue-500 text-[10px] font-semibold">📡 Ubicación GPS activa</span>}
          </p>
          {puntosOrdenados.map(punto => {
            const dist = getDistancias(punto.lat, punto.lng, userLocation, punto.distancia)
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

      {/* Bottom Sheet de detalles de punto (con z-index corregido por encima del mapa Leaflet) */}
      {selected && (
        <>
          <div className="fixed inset-0 bg-black/50 z-[9999]" onClick={() => setSelected(null)} />
          <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl">
            <div className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer" onClick={() => setSelected(null)} />
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">{selected.nombre}</h3>
            
            {(() => {
              const dist = getDistancias(selected.lat, selected.lng, userLocation, selected.distancia)
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
