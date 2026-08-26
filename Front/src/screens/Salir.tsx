// Front/src/screens/Salir.tsx
// S5 (Salir V1): pantalla conectada al producto real /products/exit.
// Sin lógica mock ni scoring local: el backend filtra, ordena por distancia
// y marca is_nearest; esta pantalla solo selecciona modo/destino y renderiza.

import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Car, Footprints, Bus, X, Map as MapIcon, ArrowRight } from 'lucide-react'
import {
  useExitRecommendations,
  type ExitZoneItem,
  type TransporteMode,
} from '@/services/exitProduct'
import { useAppStore } from '@/core/state/store'
import { NearestBadge } from '@/components/ZonaCardsList'
import { GpsModal } from '@/components/GpsModal'
import { formatUpdatedAt } from '@/utils/formatTime'
import { getDistancias } from '@/utils/geo'

const MODOS: { value: TransporteMode; label: string; icon: typeof Car }[] = [
  { value: 'vehicular', label: 'En auto', icon: Car },
  { value: 'peatonal', label: 'Caminando', icon: Footprints },
  { value: 'transporte', label: 'Colectivo', icon: Bus },
]

const getStatusChip = (status: string) => {
  switch (status) {
    case 'activa': return 'bg-success/20 text-success'
    case 'alerta': return 'bg-warning/20 text-warning'
    default: return 'bg-danger/20 text-danger'
  }
}

const Salir = () => {
  const navigate = useNavigate()
  const userLocation = useAppStore(s => s.userLocation)
  const requestLocation = useAppStore(s => s.requestLocation)

  const [mode, setMode] = useState<TransporteMode | null>(null)
  const [destinationId, setDestinationId] = useState<string | null>(null)
  const [selectedZona, setSelectedZona] = useState<ExitZoneItem | null>(null)
  const [mostrarGpsModal, setMostrarGpsModal] = useState(true)

  const { data, loading, error, refresh } = useExitRecommendations(
    destinationId ?? undefined,
    mode ?? undefined
  )

  // Refetch automático: refresh cambia de identidad cuando cambian
  // destinationId, mode o userLocation (deps del useCallback del hook).
  useEffect(() => {
    if (mode === 'transporte') return // se maneja en su propio módulo
    refresh()
  }, [refresh, mode])

  // Al cambiar de modo, se resetea la elección de destino
  useEffect(() => {
    setDestinationId(null)
  }, [mode])

  const zonas = useMemo(() => data?.zonas ?? [], [data])

  // Catálogo de destinos disponible para el modo actual, derivado de la
  // respuesta real del backend (nunca inventado en el frontend).
  const destinosDisponibles = useMemo(() => {
    const porId = new Map<string, string>()
    zonas.forEach(z =>
      z.destinations.forEach(d => {
        if (!porId.has(d.id)) porId.set(d.id, d.name)
      })
    )
    return [...porId.entries()]
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [zonas])

  const abrirMapa = (zona: ExitZoneItem) => {
    if (zona.lat && zona.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${zona.lat},${zona.lng}`,
        '_blank'
      )
    }
    setSelectedZona(null)
  }

  const puedeCalcularDistancia = (zona: ExitZoneItem) =>
    Boolean(userLocation && zona.lat && zona.lng)

  const renderDistancias = (zona: ExitZoneItem) => {
    if (!puedeCalcularDistancia(zona)) return null
    const dist = getDistancias(zona.lat!, zona.lng!, userLocation, 0)
    return (
      <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 flex gap-x-3">
        <span>🚶 Caminando: <span className="font-semibold">{dist.walking}</span></span>
        <span>🚗 En auto: <span className="font-semibold">{dist.driving}</span></span>
      </p>
    )
  }

  const renderZonaCard = (zona: ExitZoneItem) => (
    <button
      key={zona.zone_id}
      onClick={() => setSelectedZona(zona)}
      className="w-full text-left bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors shadow-sm"
    >
      <div className="flex justify-between items-center gap-2">
        <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 truncate">
          {zona.name}
        </p>
        <span className="flex items-center gap-1.5 shrink-0">
          <NearestBadge visible={zona.is_nearest} />
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getStatusChip(zona.status)}`}>
            {zona.status}
          </span>
        </span>
      </div>

      {zona.destinations.length > 0 && (
        <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">
          ➡️ {zona.destinations.map(d => d.name).join(' · ')}
        </p>
      )}

      <div className="mt-1">{renderDistancias(zona)}</div>
    </button>
  )

  const renderResultados = () => {
    if (loading) {
      return (
        <div className="py-8 text-center">
          <p className="text-sm text-slate-500">Buscando salidas...</p>
        </div>
      )
    }

    if (error) {
      return (
        <div className="py-6 flex flex-col items-center space-y-3">
          <p className="text-danger font-bold text-sm">Error al cargar</p>
          <p className="text-xs text-slate-500 text-center">{error}</p>
          <button
            onClick={refresh}
            className="bg-primary text-white px-6 py-2 rounded-lg font-bold text-sm"
          >
            Reintentar
          </button>
        </div>
      )
    }

    if (zonas.length === 0) {
      return (
        <div className="bg-white dark:bg-slate-800 border border-dashed border-slate-300 dark:border-slate-600 p-6 rounded-xl text-center">
          <p className="text-sm font-bold text-slate-700 dark:text-slate-200">
            Todavía no hay salidas configuradas
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            {destinationId
              ? 'Probá con otro destino o cambiá el modo de salida.'
              : 'Este modo aún no tiene destinos cargados.'}
          </p>
        </div>
      )
    }

    return <div className="space-y-2">{zonas.map(renderZonaCard)}</div>
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

        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2 flex items-center gap-2">
          {selectedZona.name}
          <NearestBadge visible={selectedZona.is_nearest} />
        </h3>

        <div className="space-y-2 mb-4">
          <p className="text-sm text-slate-600 dark:text-slate-300 capitalize">
            🚪 Modo de salida: {selectedZona.transporte}
          </p>
          <p className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${getStatusChip(selectedZona.status)}`}>
            Estado: {selectedZona.status}
          </p>
          {selectedZona.destinations.length > 0 && (
            <div className="text-sm text-slate-600 dark:text-slate-300">
              <p className="font-semibold mb-1">➡️ Destinos:</p>
              <ul className="list-disc list-inside">
                {selectedZona.destinations.map(d => (
                  <li key={d.id}>{d.name}</li>
                ))}
              </ul>
            </div>
          )}
          {renderDistancias(selectedZona)}
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {formatUpdatedAt(data?.timestamp ? Date.parse(data.timestamp) : Date.now())}
          </p>
        </div>

        <button
          onClick={() => abrirMapa(selectedZona)}
          disabled={!selectedZona.lat || !selectedZona.lng}
          className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2 disabled:opacity-50 disabled:pointer-events-none"
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

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Salir del evento" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 overflow-y-auto space-y-4 pb-24">
        {/* Paso 1: modo de salida */}
        <div>
          <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 mb-2">
            1️⃣ ¿Cómo vas a salir?
          </p>
          <div className="grid grid-cols-3 gap-2">
            {MODOS.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                onClick={() => setMode(value)}
                className={`flex flex-col items-center gap-1 p-3 rounded-xl border-2 transition-all active:scale-95 ${
                  mode === value
                    ? 'bg-primary text-white border-primary shadow-md'
                    : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200'
                }`}
              >
                <Icon size={22} />
                <span className="text-xs font-bold">{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Modo transporte: módulo propio (RFC §18) */}
        {mode === 'transporte' && (
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-5 rounded-xl text-center space-y-3">
            <Bus size={32} className="mx-auto text-primary" />
            <p className="text-sm font-bold text-slate-800 dark:text-slate-100">
              El transporte público se maneja en su propio módulo
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Ahí ves paradas cercanas, esperas estimadas y estado de cada línea.
            </p>
            <button
              onClick={() => navigate('/servicios/transporte')}
              className="w-full bg-primary text-white py-3 rounded-xl font-bold flex items-center justify-center gap-2 active:scale-95 transition-transform"
            >
              Ir a Transporte
              <ArrowRight size={18} />
            </button>
          </div>
        )}

        {/* Pasos 2 y 3: destino + resultados */}
        {(mode === 'vehicular' || mode === 'peatonal') && (
          <>
            <div>
              <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 mb-2">
                2️⃣ ¿Hacia dónde vas?
              </p>
              {destinosDisponibles.length === 0 ? (
                !loading && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 px-1">
                    Aún no hay destinos configurados para este modo.
                  </p>
                )
              ) : (
                <div className="flex flex-wrap gap-2">
                  {destinosDisponibles.map(destino => (
                    <button
                      key={destino.id}
                      onClick={() =>
                        setDestinationId(prev => (prev === destino.id ? null : destino.id))
                      }
                      className={`px-4 py-2 rounded-full text-sm font-bold border-2 transition-all active:scale-95 ${
                        destinationId === destino.id
                          ? 'bg-primary text-white border-primary shadow-md'
                          : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200'
                      }`}
                    >
                      {destino.name}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 mb-2">
                3️⃣ Salidas disponibles
                {!userLocation && (
                  <span className="ml-2 font-normal text-slate-400">
                    (activá el GPS para ver la más cercana)
                  </span>
                )}
              </p>
              {renderResultados()}
            </div>
          </>
        )}
      </div>

      {!userLocation && mostrarGpsModal && mode !== 'transporte' && (
        <GpsModal
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

export default Salir
