import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Phone, Globe, Map, ChevronDown, Info, List, Map as MapIcon } from 'lucide-react'
import { useAppStore } from '@/core/state/store'
import { formatUpdatedAt } from '@/utils/formatTime'
import { InteractiveMap } from '@/components/InteractiveMap'
import { getDistancias } from '@/utils/geo'
import { GpsModal } from '@/components/GpsModal'
import {
  useAccommodationRecommendations,
  type AccommodationItem,
  type AccommodationType,
} from '@/services/accommodationProduct'

const CATEGORIAS: Array<{ tipo: AccommodationType | null; icono: string; label: string }> = [
  { tipo: null, icono: '🏨', label: 'Todos' },
  { tipo: 'hotel', icono: '🏨', label: 'Hotel' },
  { tipo: 'camping', icono: '🏕️', label: 'Camping' },
  { tipo: 'hostel', icono: '🛏️', label: 'Hostel' },
  { tipo: 'other', icono: '🏠', label: 'Otros' },
]

const BADGE_TYPE: Record<AccommodationType, string> = {
  hotel: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  hostel: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
  camping: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  other: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
}

const Pernoctar = () => {
  const navigate = useNavigate()
  const [categoriaActiva, setCategoriaActiva] = useState<AccommodationType | null>(null)
  const { data, loading, error, refresh } = useAccommodationRecommendations(categoriaActiva ?? undefined)
  const [selectedPunto, setSelectedPunto] = useState<AccommodationItem | null>(null)
  const [showMap, setShowMap] = useState(false)
  const [mostrarTodos, setMostrarTodos] = useState(false)
  const [mostrarGpsModal, setMostrarGpsModal] = useState(true)
  const userLocation = useAppStore(s => s.userLocation)
  const requestLocation = useAppStore(s => s.requestLocation)

  useEffect(() => {
    refresh()
  }, [refresh])

  const alojamientos = data?.accommodations ?? []
  const mostrados = mostrarTodos ? alojamientos : alojamientos.slice(0, 3)

  const handleMaps = (lat: number, lng: number) => {
    const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
    window.open(url, '_blank')
  }

  const getCategoriaLabel = (tipo: AccommodationType): string => {
    switch (tipo) {
      case 'hotel': return 'Hotel'
      case 'hostel': return 'Hostel'
      case 'camping': return 'Camping'
      default: return 'Otros'
    }
  }

  const getUrlMasInfo = (p: AccommodationItem): string | null => {
    return p.website || p.official_info_url || null
  }

  const esMasCercano = (p: AccommodationItem, index: number): boolean => {
    return !!userLocation && index === 0 && !!p.latitude && !!p.longitude
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Hospedajes" showBack onBack={() => navigate('/')} />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-500 dark:text-slate-300">Buscando alojamientos...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Hospedajes" showBack onBack={() => navigate('/')} />
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

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Hospedajes" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-3 overflow-y-auto pb-20">
        <p className="text-xs text-slate-500 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/50 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 flex items-center gap-2">
          <Info size={14} /> Elegí una categoría para ver los alojamientos disponibles
        </p>

        {/* Paso 1 — Selector de categoría */}
        <div className="grid grid-cols-2 gap-2">
          {CATEGORIAS.map(cat => {
            const activa = categoriaActiva === cat.tipo
            return (
              <button
                key={cat.label}
                onClick={() => setCategoriaActiva(cat.tipo)}
                className={`flex flex-col items-center justify-center gap-1 p-3 rounded-xl border-2 transition-transform active:scale-95 ${
                  activa
                    ? 'bg-primary text-white border-primary shadow-lg shadow-primary/25'
                    : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500'
                }`}
              >
                <span className="text-2xl">{cat.icono}</span>
                <span className="text-sm font-bold">{cat.label}</span>
              </button>
            )
          })}
        </div>

        {alojamientos.length === 0 && !loading && (
          <div className="text-center text-slate-500 dark:text-slate-300 py-8">
            No hay alojamientos de este tipo disponibles
          </div>
        )}

        {/* Paso 2 — Lista de alojamientos */}
        {showMap ? (
          <div className="space-y-4">
            <InteractiveMap
              puntos={alojamientos
                .filter(a => a.latitude && a.longitude)
                .map((a, index) => ({
                  id: a.id,
                  nombre: a.name,
                  lat: a.latitude!,
                  lng: a.longitude!,
                  referencia: a.reference || a.address || '',
                  tipo: 'hospedaje',
                  originalData: { ...a, index },
                }))}
              onSelectPunto={(p) => setSelectedPunto(p.originalData as AccommodationItem)}
              onUserLocationUpdate={() => {}}
            />
          </div>
        ) : (
          mostrados.map((p, index) => {
            const dist = getDistancias(p.latitude ?? 0, p.longitude ?? 0, userLocation, 0)
            return (
              <button
                key={p.id}
                onClick={() => setSelectedPunto(p)}
                className="w-full text-left bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors group shadow-sm flex items-start gap-2"
              >
                <span className="text-lg mt-0.5">🏨</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">
                      {p.name}
                    </p>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${BADGE_TYPE[p.type]}`}>
                      {getCategoriaLabel(p.type).toUpperCase()}
                    </span>
                    {esMasCercano(p, index) && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-success/20 text-success">
                        📍 Más cercano
                      </span>
                    )}
                  </div>
                  {p.address && (
                    <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 truncate">
                      {p.address}
                    </p>
                  )}
                  {p.reference && (
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 truncate">
                      {p.reference}
                    </p>
                  )}
                  <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 flex flex-wrap gap-x-2 gap-y-0.5 items-center">
                    <span>🚶 {dist.walking}</span>
                    <span className="opacity-50">·</span>
                    <span>🚗 {dist.driving}</span>
                    {!userLocation && <span className="opacity-50">· ordenado por nombre</span>}
                  </p>
                </div>
                <Info size={16} className="text-slate-400 flex-shrink-0" />
              </button>
            )
          })
        )}

        {/* Paso 2 — CTA por cada alojamiento (botones grandes) */}
        {!showMap && mostrados.map((p, index) => {
          const urlInfo = getUrlMasInfo(p)
          return (
            <div key={`cta-${p.id}`} className="bg-white dark:bg-slate-800 p-4 rounded-xl shadow-md space-y-2">
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-bold text-slate-800 dark:text-slate-100">{p.name}</p>
                  <div className="text-sm font-semibold text-slate-500 dark:text-slate-300">
                    {getCategoriaLabel(p.type).toUpperCase()}
                  </div>
                  <p className="text-sm text-slate-500 dark:text-slate-300">
                    {p.reference || p.address || ''}
                  </p>
                </div>
                {esMasCercano(p, index) && (
                  <span className="px-2 py-1 rounded text-[10px] font-bold bg-success/20 text-success">
                    📍 Más cercano
                  </span>
                )}
              </div>

              <p className="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-1">
                <Map size={14} /> {getDistancias(p.latitude ?? 0, p.longitude ?? 0, userLocation, 0).walking} · 🚗 {getDistancias(p.latitude ?? 0, p.longitude ?? 0, userLocation, 0).driving}
              </p>
              <p className="text-xs text-slate-400 dark:text-slate-300">
                {formatUpdatedAt(Date.now())}
              </p>

              <div className="flex gap-2 pt-2">
                {p.phone && (
                  <a
                    href={`tel:${p.phone}`}
                    className="flex-1 flex items-center justify-center gap-1 bg-success/15 dark:bg-success/25 hover:bg-success/25 dark:hover:bg-success/35 text-success font-bold py-2 rounded-xl text-sm transition-colors"
                  >
                    <Phone size={16} /> Llamar
                  </a>
                )}

                {urlInfo && (
                  <a
                    href={urlInfo}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 flex items-center justify-center gap-1 bg-primary text-white hover:bg-primary/90 py-2 rounded-xl font-bold text-sm transition-colors shadow-lg shadow-primary/25"
                  >
                    <Globe size={16} /> Más info
                  </a>
                )}
              </div>
            </div>
          )
        })}

        {/* Botón Ver más */}
        {!showMap && !mostrarTodos && alojamientos.length > 3 && (
          <button
            onClick={() => setMostrarTodos(true)}
            className="w-full bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 py-3 rounded-xl font-bold transition-transform active:scale-95 border-2 border-slate-300 dark:border-slate-600 flex items-center justify-center gap-2"
          >
            <ChevronDown size={18} />
            Ver {alojamientos.length - 3} alojamientos más
          </button>
        )}

        {!showMap && mostrarTodos && alojamientos.length > 3 && (
          <button
            onClick={() => setMostrarTodos(false)}
            className="w-full bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 py-3 rounded-xl font-bold transition-transform active:scale-95 border-2 border-slate-300 dark:border-slate-600"
          >
            Mostrar menos
          </button>
        )}
      </div>

      {/* Botón flotante para alternar Mapa/Lista */}
      <button
        onClick={() => setShowMap(!showMap)}
        className="fixed bottom-4 right-4 bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 px-4 rounded-full font-bold shadow-lg flex items-center gap-2 z-30 transition-transform active:scale-95 text-sm"
      >
        {showMap ? <List size={20} /> : <MapIcon size={20} />}
        {showMap ? 'Ver lista' : 'Ver mapa completo'}
      </button>

      {/* Paso 3 — Bottom Sheet de detalles */}
      {selectedPunto && (
        <>
          <div className="fixed inset-0 bg-black/50 z-[9999]" onClick={() => setSelectedPunto(null)} />
          <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl space-y-4">
            <div className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-2 cursor-pointer" onClick={() => setSelectedPunto(null)} />

            <div>
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">{selectedPunto.name}</h3>
                  <p className="text-sm font-semibold text-slate-500 dark:text-slate-300">
                    {getCategoriaLabel(selectedPunto.type).toUpperCase()}
                  </p>
                </div>
              </div>
              {selectedPunto.address && (
                <p className="text-sm text-slate-600 dark:text-slate-300 mt-2">📍 {selectedPunto.address}</p>
              )}
              {selectedPunto.reference && (
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{selectedPunto.reference}</p>
              )}
              {(() => {
                const dist = getDistancias(selectedPunto.latitude ?? 0, selectedPunto.longitude ?? 0, userLocation, 0)
                return (
                  <div className="space-y-1.5 mt-2 text-sm text-slate-600 dark:text-slate-300">
                    <p className="flex items-center gap-1.5">🚶 <span>Tiempo caminando:</span> <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span></p>
                    <p className="flex items-center gap-1.5">🚗 <span>Tiempo en auto:</span> <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span></p>
                  </div>
                )
              })()}
              <p className="text-xs text-slate-400 dark:text-slate-400 mt-2">
                {formatUpdatedAt(Date.now())}
              </p>
            </div>

            <div className="flex flex-col gap-2">
              <button
                onClick={() => selectedPunto.latitude && selectedPunto.longitude && handleMaps(selectedPunto.latitude, selectedPunto.longitude)}
                className="w-full flex items-center justify-center gap-1 bg-primary text-white hover:bg-primary/90 py-2.5 rounded-xl font-bold text-sm transition-colors shadow-lg shadow-primary/25"
              >
                <Map size={16} /> Ver en Mapa
              </button>

              <div className="flex gap-2">
                {selectedPunto.phone && (
                  <a
                    href={`tel:${selectedPunto.phone}`}
                    className="flex-1 flex items-center justify-center gap-1 bg-success/15 dark:bg-success/25 hover:bg-success/25 dark:hover:bg-success/35 text-success font-bold py-2.5 rounded-xl text-sm transition-colors"
                  >
                    <Phone size={16} /> Llamar
                  </a>
                )}

                {getUrlMasInfo(selectedPunto) && (
                  <a
                    href={getUrlMasInfo(selectedPunto)!}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 flex items-center justify-center gap-1 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-600 py-2.5 rounded-xl font-bold text-sm transition-colors"
                  >
                    <Globe size={16} /> Más info
                  </a>
                )}
              </div>
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

      {!userLocation && mostrarGpsModal && (
        <GpsModal
          mensaje="Para mostrarte el alojamiento más cercano, necesitamos tu ubicación GPS."
          onActivate={() => {
            requestLocation()
            setMostrarGpsModal(false)
          }}
          onClose={() => setMostrarGpsModal(false)}
        />
      )}
    </div>
  )
}

export default Pernoctar
