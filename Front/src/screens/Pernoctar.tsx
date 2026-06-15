import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Phone, Map, ChevronDown, Info, Clock, List, Map as MapIcon } from 'lucide-react'
import { getPernoctesOrdenados } from '@/utils/pernoctar'
import { useAppStore } from '@/core/state/store'
import { mapZonesToPernoctar, type PuntoPernoctar } from '@/data/mappers'
import { eventoData } from '@/data/eventoData'
import { formatUpdatedAt } from '@/utils/formatTime'
import { InteractiveMap } from '@/components/InteractiveMap'
import { getDistancias, haversine } from '@/utils/geo'
import { useUserLocation } from '@/hooks/useUserLocation'

const Pernoctar = () => {
  const navigate = useNavigate()
  const zones = useAppStore(s => s.zones)
  const userLocation = useUserLocation()
  const pernoctar: PuntoPernoctar[] = useMemo(() => {
    const mapped = mapZonesToPernoctar(zones)
    return mapped.length > 0 ? mapped : eventoData.pernoctar
  }, [zones])
  const puntos = useMemo(() => {
    const ordenadosOriginales = getPernoctesOrdenados(pernoctar)
    if (userLocation) {
      return [...ordenadosOriginales].sort((a, b) => {
        if (a.lat && a.lng && b.lat && b.lng) {
          const distA = haversine(userLocation[0], userLocation[1], a.lat, a.lng)
          const distB = haversine(userLocation[0], userLocation[1], b.lat, b.lng)
          return distA - distB
        }
        return 0
      })
    }
    return ordenadosOriginales
  }, [pernoctar, userLocation])
  const [mostrarTodos, setMostrarTodos] = useState(false)
  const [showMap, setShowMap] = useState(false)
  const [selectedPunto, setSelectedPunto] = useState<PuntoPernoctar | null>(null)

  const handleMaps = (lat: number, lng: number) => {
    const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
    window.open(url, '_blank')
  }

  const getDispBadge = (disp?: string) => {
    switch (disp) {
      case 'disponible': return 'bg-success/20 text-success'
      case 'completo': return 'bg-danger/20 text-danger'
      default: return 'bg-warning/20 text-warning'
    }
  }

  const getDispText = (disp?: string) => {
    switch (disp) {
      case 'disponible': return '🟢 Probable disponibilidad'
      case 'completo': return '🔴 Últimos lugares'
      default: return '🟡 Consultar disponibilidad'
    }
  }

  const mostrados = mostrarTodos ? puntos : puntos.slice(0, 3)

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Hospedajes" showBack onBack={() => navigate('/')} />

      {showMap ? (
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          <InteractiveMap
            puntos={puntos.map(p => ({
              id: p.id,
              nombre: p.nombre,
              lat: p.lat,
              lng: p.lng,
              referencia: p.referencia,
              tipo: 'hospedaje',
              originalData: p
            }))}
            onSelectPunto={setSelectedPunto}
            onUserLocationUpdate={() => {}}
          />

          {/* Lista de alojamientos */}
          <div className="space-y-2 pb-16">
            <p className="text-xs font-bold text-slate-600 dark:text-slate-400 px-1 flex justify-between">
              <span>📍 {puntos.length} alojamientos disponibles</span>
              {userLocation && <span className="text-blue-500 text-[10px] font-semibold">📡 Ubicación GPS activa</span>}
            </p>
            {puntos.map(p => {
              const dist = getDistancias(p.lat, p.lng, userLocation, p.distancia_min)
              return (
                <button
                  key={p.id}
                  onClick={() => setSelectedPunto(p)}
                  className="w-full text-left bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors group shadow-sm flex items-start gap-2"
                >
                  <span className="text-lg mt-0.5">🏨</span>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">
                      {p.nombre}
                    </p>
                    <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 flex flex-wrap gap-x-2 gap-y-0.5 items-center">
                      <span>🚶 {dist.walking}</span>
                      <span className="opacity-50">·</span>
                      <span>🚗 {dist.driving}</span>
                      <span className="opacity-50">·</span>
                      <span className="truncate">{p.referencia}</span>
                    </p>
                  </div>
                  <Info size={16} className="text-slate-400 flex-shrink-0" />
                </button>
              )
            })}
          </div>
        </div>
      ) : (
        <div className="flex-1 p-4 space-y-3 overflow-y-auto pb-20">
          {/* Microcopy informativo */}
          <p className="text-xs text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/50 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 flex items-center gap-2">
            <Info size={14} /> Los alojamientos pueden variar su disponibilidad durante el evento
          </p>

          {mostrados.map(p => (
            <div key={p.id} className="bg-white dark:bg-slate-800 p-4 rounded-xl shadow-md space-y-2">
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-bold text-slate-800 dark:text-slate-100">{p.nombre}</p>
                  <div className="text-sm font-semibold text-slate-500 dark:text-slate-400">
                    {(p.categoria ?? '').toUpperCase()}
                  </div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    · {p.referencia}
                  </p>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-bold ${getDispBadge(p.disponibilidad)}`}>
                  {getDispText(p.disponibilidad)}
                </span>
              </div>

              <p className="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-1">
                <Clock size={14} /> {p.distancia_min} min
              </p>
              <p className="text-xs text-slate-400 dark:text-slate-500">
                {formatUpdatedAt(p.updatedAt)}
              </p>
              <p className="text-xs text-gray-500 flex items-center gap-1">
                <Info size={12} /> Confirmar disponibilidad por teléfono antes de ir
              </p>

              <div className="flex gap-2 pt-2">
                {p.telefono && (
                  <a
                    href={`tel:${p.telefono}`}
                    className="flex-1 flex items-center justify-center gap-1 bg-success/10 hover:bg-success/20 text-success py-2 rounded-xl font-bold text-sm transition-colors"
                  >
                    <Phone size={16} /> Llamar
                  </a>
                )}

                <button
                  onClick={() => handleMaps(p.lat, p.lng)}
                  className="flex-1 flex items-center justify-center gap-1 bg-primary/10 hover:bg-primary/20 text-primary py-2 rounded-xl font-bold text-sm transition-colors"
                >
                  <Map size={16} /> Ir ahora
                </button>
              </div>
            </div>
          ))}

          {puntos.length === 0 && (
            <div className="text-center text-slate-500 dark:text-slate-400 py-8">
              No hay alojamientos registrados
            </div>
          )}

          {/* Botón Ver más */}
          {!mostrarTodos && puntos.length > 3 && (
            <button
              onClick={() => setMostrarTodos(true)}
              className="w-full bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 py-3 rounded-xl font-bold transition-transform active:scale-95 border-2 border-slate-300 dark:border-slate-600 flex items-center justify-center gap-2"
            >
              <ChevronDown size={18} />
              Ver {puntos.length - 3} alojamientos más
            </button>
          )}

          {mostrarTodos && puntos.length > 3 && (
            <button
              onClick={() => setMostrarTodos(false)}
              className="w-full bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 py-3 rounded-xl font-bold transition-transform active:scale-95 border-2 border-slate-300 dark:border-slate-600"
            >
              Mostrar menos
            </button>
          )}
        </div>
      )}

      {/* Botón flotante para alternar Mapa/Lista */}
      <button
        onClick={() => setShowMap(!showMap)}
        className="fixed bottom-4 right-4 bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 px-4 rounded-full font-bold shadow-lg flex items-center gap-2 z-30 transition-transform active:scale-95 text-sm"
      >
        {showMap ? <List size={20} /> : <MapIcon size={20} />}
        {showMap ? 'Ver lista' : 'Ver mapa completo'}
      </button>

      {/* Bottom Sheet de detalles de alojamiento */}
      {selectedPunto && (
        <>
          <div className="fixed inset-0 bg-black/50 z-[9999]" onClick={() => setSelectedPunto(null)} />
          <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl space-y-4">
            <div className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-2 cursor-pointer" onClick={() => setSelectedPunto(null)} />
            
            <div>
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">{selectedPunto.nombre}</h3>
                  <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">{(selectedPunto.categoria ?? '').toUpperCase()}</p>
                </div>
                <span className={`px-2 py-1 rounded text-[10px] font-bold ${getDispBadge(selectedPunto.disponibilidad)}`}>
                  {getDispText(selectedPunto.disponibilidad)}
                </span>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-300 mt-2">📍 {selectedPunto.referencia}</p>
              {(() => {
                const dist = getDistancias(selectedPunto.lat, selectedPunto.lng, userLocation, selectedPunto.distancia_min)
                return (
                  <div className="space-y-1.5 mt-2 text-sm text-slate-600 dark:text-slate-300">
                    <p className="flex items-center gap-1.5">🚶 <span>Tiempo caminando:</span> <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span></p>
                    <p className="flex items-center gap-1.5">🚗 <span>Tiempo en auto:</span> <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span></p>
                  </div>
                )
              })()}
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
                {formatUpdatedAt(selectedPunto.updatedAt)}
              </p>
            </div>

            <div className="flex gap-2">
              {selectedPunto.telefono && (
                <a
                  href={`tel:${selectedPunto.telefono}`}
                  className="flex-1 flex items-center justify-center gap-1 bg-success/10 hover:bg-success/20 text-success py-2.5 rounded-xl font-bold text-sm transition-colors"
                >
                  <Phone size={16} /> Llamar
                </a>
              )}

              <button
                onClick={() => handleMaps(selectedPunto.lat, selectedPunto.lng)}
                className="flex-1 flex items-center justify-center gap-1 bg-primary/10 hover:bg-primary/20 text-primary py-2.5 rounded-xl font-bold text-sm transition-colors"
              >
                <Map size={16} /> Ir ahora
              </button>
            </div>

            <button
              onClick={() => setSelectedPunto(null)}
              className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold text-sm transition-transform active:scale-95"
            >
              Cerrar
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default Pernoctar
