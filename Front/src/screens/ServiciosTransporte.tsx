import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Map, X } from 'lucide-react'
import { useAppStore } from '@/core/state/store'
import {
  useTransportRecommendations,
  useAvailableDestinations,
  type ZonaTransporteItem,
  type TransportType,
} from '@/services/transportProduct'
import { NearestBadge } from '@/components/ZonaCardsList'
import { GpsModal } from '@/components/GpsModal'
import { formatUpdatedAt } from '@/utils/formatTime'
import { getDistancias } from '@/utils/geo'

const TIPOS: { valor: TransportType; etiqueta: string; icono: string }[] = [
  { valor: 'urbano', etiqueta: 'Urbano', icono: '🚌' },
  { valor: 'interurbano', etiqueta: 'Interurbano', icono: '🚍' },
]

const ServiciosTransporte = () => {
  const navigate = useNavigate()
  const [tipo, setTipo] = useState<TransportType | null>(null)
  const [destino, setDestino] = useState<string>('Todos')

  const {
    data: destinosData,
    loading: cargandoDestinos,
  } = useAvailableDestinations(tipo ?? undefined)

  const {
    data,
    loading,
    error,
    refresh,
  } = useTransportRecommendations(
    destino === 'Todos' ? undefined : destino,
    tipo ?? undefined
  )

  const [selectedZona, setSelectedZona] = useState<ZonaTransporteItem | null>(null)
  const [mostrarGpsModal, setMostrarGpsModal] = useState(true)
  const userLocation = useAppStore(s => s.userLocation)
  const requestLocation = useAppStore(s => s.requestLocation)

  useEffect(() => {
    refresh()
  }, [refresh])

  // Reset destino when the type changes
  useEffect(() => {
    setDestino('Todos')
  }, [tipo])

  const zonas = data?.zonas ?? []
  const timestamp = data?.timestamp ? Date.parse(data.timestamp) : Date.now()
  const destinos = destinosData?.destinations ?? []

  const abrirMapa = (zona: ZonaTransporteItem) => {
    if (zona.lat && zona.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${zona.lat},${zona.lng}`,
        '_blank'
      )
    }
    setSelectedZona(null)
  }

  const renderHorario = (zona: ZonaTransporteItem) => {
    if (!zona.next_departure) {
      return <p className="text-xs text-slate-500 dark:text-slate-300 mt-1">🚫 Sin servicios programados para este horario</p>
    }
    const prefijo = zona.is_tomorrow ? 'mañana ' : ''
    const sufijo = zona.minutes_until_next != null ? ` (en ${zona.minutes_until_next} min)` : ''
    return (
      <p
        className={`text-xs mt-1 ${
          zona.is_tomorrow
            ? 'text-blue-600 dark:text-blue-400 font-semibold'
            : 'text-slate-700 dark:text-slate-200'
        }`}
      >
        {zona.is_tomorrow ? '🌙 ' : '🚌 '}Próximo servicio: <span className="font-semibold">{prefijo}{zona.next_departure}{sufijo}</span>
      </p>
    )
  }

  const renderCard = (zona: ZonaTransporteItem) => {
    const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min ?? 5)
    return (
      <button
        key={zona.zone_id}
        onClick={() => setSelectedZona(zona)}
        className="w-full text-left bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors shadow-sm flex items-start gap-2"
      >
        <span className="text-lg mt-0.5">🚌</span>
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-center gap-2">
            <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 truncate">
              {zona.name}
            </p>
            <NearestBadge visible={zona.is_nearest} />
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-300 mt-0.5">
            {zona.line_name ?? 'Línea sin nombre'}
            {zona.company ? ` · ${zona.company}` : ''}
          </p>
          {renderHorario(zona)}
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 flex flex-wrap gap-x-2 gap-y-0.5 items-center">
            {zona.destination && <span>🎯 {zona.destination}</span>}
            {zona.distancia_min != null && <span>· 📏 {zona.distancia_min} m</span>}
            <span>· 🚶 {dist.walking}</span>
            <span>· 🚗 {dist.driving}</span>
          </p>
        </div>
      </button>
    )
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

        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-1">
          {selectedZona.name}
        </h3>
        <p className="text-sm text-slate-500 dark:text-slate-300 mb-4">
          {selectedZona.line_name ?? 'Línea sin nombre'} · {selectedZona.company ?? 'Empresa'}
        </p>

        <div className="space-y-2 mb-4">
          {renderHorario(selectedZona)}
          {selectedZona.destination && (
            <p className="text-sm text-slate-600 dark:text-slate-300">
              🎯 Destino: <span className="font-semibold">{selectedZona.destination}</span>
            </p>
          )}
          <p className="text-sm text-slate-600 dark:text-slate-300">
            📍 {selectedZona.referencia}
          </p>
          {selectedZona.distancia_min != null && (
            <p className="text-sm text-slate-600 dark:text-slate-300">
              📏 Distancia: <span className="font-semibold">{selectedZona.distancia_min} m</span>
              <NearestBadge visible={selectedZona.is_nearest} />
            </p>
          )}
          {(() => {
            const dist = getDistancias(selectedZona.lat ?? 0, selectedZona.lng ?? 0, userLocation, selectedZona.distancia_min ?? 5)
            return (
              <>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🚶 Caminando: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.walking}</span>
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🚗 En auto: <span className="font-semibold text-slate-800 dark:text-slate-100">{dist.driving}</span>
                </p>
              </>
            )
          })()}
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {formatUpdatedAt(timestamp)}
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

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Transporte" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {/* PASO 1: Selector de tipo */}
        {!tipo ? (
          <div className="space-y-4">
            <div className="bg-white dark:bg-slate-800 p-5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm text-center">
              <p className="text-3xl mb-2">🚌</p>
              <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">
                ¿Qué tipo de transporte necesitás?
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-300 mt-1">
                Seleccioná una opción para ver los servicios disponibles.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 px-1">
              {TIPOS.map(t => (
                <button
                  key={t.valor}
                  onClick={() => setTipo(t.valor)}
                  className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 rounded-xl p-4 shadow-sm transition-colors flex flex-col items-center gap-1"
                >
                  <span className="text-3xl">{t.icono}</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-100">
                    {t.etiqueta}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {/* PASO 2: Selector de destino (dinámico) */}
            <div>
              <div className="flex items-center justify-between px-1">
                <p className="text-xs font-bold text-slate-600 dark:text-slate-300 mb-2">
                  🎯 ¿A dónde vas?
                </p>
                <button
                  onClick={() => setTipo(null)}
                  className="text-xs text-slate-500 dark:text-slate-400 underline"
                >
                  Cambiar tipo
                </button>
              </div>
              {cargandoDestinos ? (
                <p className="text-sm text-slate-500 italic px-1">Cargando destinos...</p>
              ) : (
                <div className="flex flex-wrap gap-2 px-1">
                  <button
                    key="todos"
                    onClick={() => setDestino('Todos')}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                      destino === 'Todos'
                        ? 'bg-primary text-white'
                        : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    Todos
                  </button>
                  {destinos.map(d => (
                    <button
                      key={d}
                      onClick={() => setDestino(d)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                        destino === d
                          ? 'bg-primary text-white'
                          : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      {d}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {!userLocation && mostrarGpsModal && (
              <GpsModal
                mensaje="Para mostrarte la parada de transporte más cercana, necesitamos tu ubicación GPS."
                onActivate={() => {
                  requestLocation()
                  setMostrarGpsModal(false)
                }}
                onClose={() => setMostrarGpsModal(false)}
              />
            )}

            {/* PASO 3: Lista de paradas */}
            {loading ? (
              <div className="py-10 text-center">
                <p className="text-slate-500">Cargando horarios de transporte...</p>
              </div>
            ) : error ? (
              <div className="p-4 flex flex-col items-center space-y-4 bg-slate-100 dark:bg-slate-700 rounded-xl">
                <p className="text-danger font-bold">Error al cargar</p>
                <p className="text-sm text-slate-500 dark:text-slate-300 text-center">{error}</p>
                <button onClick={refresh} className="bg-primary text-white px-6 py-2 rounded-lg font-bold">
                  Reintentar
                </button>
              </div>
            ) : data?.mode === 'sin_solucion' || zonas.length === 0 ? (
              <div className="bg-slate-100 dark:bg-slate-700 p-6 rounded-xl text-center space-y-2">
                <p className="text-lg font-bold text-slate-800 dark:text-slate-100">
                  🚌 No hay servicios de transporte disponibles hacia ese destino en este horario
                </p>
                <p className="text-sm text-slate-500 dark:text-slate-300">
                  Probá otro destino o consultá más tarde.
                </p>
              </div>
            ) : (
              <div className="space-y-2 pb-16">
                <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 flex justify-between">
                  <span>🚌 {zonas.length} paradas de transporte disponibles</span>
                  {userLocation && <span className="text-blue-500 text-[10px] font-semibold">📡 Ubicación GPS activa</span>}
                </p>
                {zonas.map(renderCard)}
              </div>
            )}
          </>
        )}
      </div>

      {renderBottomSheet}
    </div>
  )
}

export default ServiciosTransporte
