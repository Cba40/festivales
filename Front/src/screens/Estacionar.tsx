import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { AppFooter } from '@/components/AppFooter'
import { Map, X } from 'lucide-react'
import { InteractiveMap, type InteractiveMapPoint } from '@/components/InteractiveMap'
import { useAppStore } from '@/core/state/store'
import {
  useParkingRecommendations,
  PARKING_LIMIT,
  DISTANCIA_FALLBACK_MIN,
  type ZonaEstacionamientoItem,
} from '@/services/parkingProduct'
import {
  ZonaCardsList,
  getEstadoStyles,
  getEstadoLabel,
  getConfianzaLabel,
  NearestBadge,
} from '@/components/ZonaCardsList'
import { GpsModal } from '@/components/GpsModal'
import { recordActivity } from '@/services/activity'
import { formatUpdatedAt } from '@/utils/formatTime'
import { getDistancias } from '@/utils/geo'

/**
 * Porcentaje de "posibilidad" por debajo del cual se avisa que la disponibilidad
 * está limitada. Es un umbral de presentación: el número sale del backend y acá
 * solo se decide si se muestra el aviso.
 */
const AVAILABILITY_WARNING_THRESHOLD = 20

/**
 * Cuántas zonas listar en la rama `sin_solucion`.
 *
 * Deliberadamente **desacoplado** de `PARKING_LIMIT`: ese constant es cuántas
 * pedimos al backend, este es cuántas mostramos en la lista de disponibilidad
 * limitada. Acoplarlos con `PARKING_LIMIT - 1` haría que subir el limit de 4 a 5
 * mostrara 4 avisos donde antes mostraba 3, sin que nadie lo pidiera.
 */
const ZONAS_MAX_SIN_SOLUCION = 3

/**
 * Espera orientativa cuando **no hay ninguna zona** que aporte un
 * `estimated_wait`: en la rama `sin_solucion` con `zonas.length === 0` no hay de
 * dónde leer un dato dinámico, así que el texto es una estimación fija y
 * documentada, no un valor hardcodeado sin contexto.
 */
const DEFAULT_WAIT_ESTIMATE = '⏱️ Esperar 20–30 min'

/**
 * Fila de métricas de una zona: tiempo en auto y posibilidad de estacionamiento.
 *
 * Reemplaza 4 copias idénticas de un IIFE que solo cambiaba el nombre de la
 * variable. `className` existe porque la tarjeta principal va sobre fondo de
 * color en modo `guiar` y necesita `opacity-90` en vez de los colores de texto.
 */
const FilaMetricas = ({
  zona,
  className,
}: {
  zona: ZonaEstacionamientoItem
  className?: string
}) => {
  const userLocation = useAppStore(s => s.userLocation)
  const dist = getDistancias(
    zona.lat,
    zona.lng,
    userLocation,
    zona.distancia_min ?? DISTANCIA_FALLBACK_MIN
  )
  return (
    <p className={`flex gap-3 ${className ?? 'text-sm text-slate-600 dark:text-slate-300'}`}>
      <span>🚗 {dist.driving}</span>
      {zona.saturation_level != null && (
        <span>📊 {Math.round((1 - zona.saturation_level) * 100)}% de posibilidad</span>
      )}
    </p>
  )
}

const Estacionar = () => {
  const navigate = useNavigate()
  const { data, loading, error, refresh } = useParkingRecommendations()
  const [selectedZona, setSelectedZona] = useState<ZonaEstacionamientoItem | null>(null)
  const [mostrarGpsModal, setMostrarGpsModal] = useState(true)
  const userLocation = useAppStore(s => s.userLocation)
  const requestLocation = useAppStore(s => s.requestLocation)
  const lastEmittedZone = useRef<string | null>(null)

  useEffect(() => {
    refresh()
  }, [refresh])

  const zonas = data?.zonas ?? []

  const modo = data?.mode ?? 'informar'

  const principal = zonas[0]
  const alternativa = zonas[1]
  const terceraOpcion = zonas[2]
  const cuartaOpcion = zonas[3]

  // Elegir zona de estacionamiento es la decisión de mayor valor del módulo:
  // habilita saber qué punto genera demanda. "Iniciar ruta" desde el detalle no
  // vuelve a emitir: la zona ya quedó contada al abrir la tarjeta.
  const handleSelectZona = (zona: ZonaEstacionamientoItem) => {
    if (lastEmittedZone.current !== zona.zone_id) {
      lastEmittedZone.current = zona.zone_id
      recordActivity({
        interaction_type: 'filter_change',
        service_category: 'parking',
        request_mode: `zona=${zona.zone_id}`,
      })
    }
    setSelectedZona(zona)
  }

  const abrirMapa = (zona: ZonaEstacionamientoItem) => {
    // `!= null` y no truthiness: una zona en el ecuador (lat 0) o sobre el
    // meridiano de Greenwich (lng 0) es una zona válida con navegación.
    if (zona.lat != null && zona.lng != null) {
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

  // El prompt de GPS se resolvía en dos ramas distintas (la de `sin_solucion` y
  // el return principal) con el mismo mensaje y los mismos callbacks.
  const gpsPrompt = !userLocation && mostrarGpsModal && (
    <GpsModal
      mensaje="Para mostrarte la opción de estacionamiento más cercana, necesitamos tu ubicación GPS."
      onActivate={() => {
        requestLocation()
        setMostrarGpsModal(false)
      }}
      onClose={() => setMostrarGpsModal(false)}
    />
  )

  const renderBottomSheet = selectedZona && (
    <>
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={() => setSelectedZona(null)}
      />
      <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
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
            const dist = getDistancias(selectedZona.lat, selectedZona.lng, userLocation, selectedZona.distancia_min ?? DISTANCIA_FALLBACK_MIN)
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

  if (data === null && error && !loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Estacionar" showBack onBack={() => navigate('/')} />
        <div className="flex-1 p-4 flex flex-col items-center justify-center space-y-4">
          <p className="text-danger font-bold">Error al cargar</p>
          <p className="text-sm text-slate-500 text-center">{error}</p>
          <button
            onClick={() => refresh(true, 'user')}
            className="bg-primary text-white px-6 py-2 rounded-lg font-bold"
          >
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  if (data === null) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Estacionar" showBack onBack={() => navigate('/')} />
        <div className="flex-1 p-4 flex items-center justify-center" aria-live="polite">
          <p className="text-slate-500">Cargando recomendaciones...</p>
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

          {gpsPrompt}

          {zonas.length === 0 && (
            <div className="bg-slate-100 dark:bg-slate-700 p-4 rounded-xl space-y-3">
              <button className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform">
                {DEFAULT_WAIT_ESTIMATE}
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
              {zonas.slice(0, ZONAS_MAX_SIN_SOLUCION).map((zona, index) => {
                const dist = getDistancias(zona.lat, zona.lng, userLocation, zona.distancia_min ?? DISTANCIA_FALLBACK_MIN)
                return (
                  <button
                    key={zona.zone_id}
                    onClick={() => handleSelectZona(zona)}
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
  const listaRestante = esTresOpciones ? zonas.slice(PARKING_LIMIT) : zonas.slice(1)

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
            onClick={() => { handleSelectZona(principal); abrirMapa(principal) }}
            className="w-full bg-primary hover:bg-primary-dark text-white p-6 rounded-2xl shadow-lg transition-transform active:scale-95"
          >
            <div className="flex items-center justify-between">
              <div className="text-left flex-1">
                <p className="text-2xl font-bold mb-1">IR AHORA</p>
                <p className="text-lg opacity-90">{principal.name}</p>
                <p className="text-sm opacity-75 mt-1">
                  🚗 {getDistancias(principal.lat, principal.lng, userLocation, principal.distancia_min ?? DISTANCIA_FALLBACK_MIN).driving}
                  {principal.saturation_level != null && ` · 📊 ${Math.round((1 - principal.saturation_level) * 100)}% libre`}
                </p>
              </div>
              <div className="text-4xl">🧭</div>
            </div>
          </button>
        )}

        {esTresOpciones && principal && (
          <button onClick={() => handleSelectZona(principal)} className="w-full">
            <div className={modo === 'guiar'
              ? 'bg-primary text-white p-6 rounded-xl text-left shadow-lg'
              : 'bg-white dark:bg-slate-800 border-l-4 border-primary p-4 rounded-xl text-left shadow-md'}>
              <p className={`font-bold text-lg ${modo === 'asistir' ? 'text-slate-800 dark:text-slate-100' : ''}`}>
                {getTituloZona(0)}: {principal.name}
              </p>
              <p className="text-sm opacity-90 mt-2">📍 {principal.referencia}</p>
              <FilaMetricas zona={principal} className="text-sm opacity-90" />
              {Math.round((1 - (principal.saturation_level ?? 0)) * 100) < AVAILABILITY_WARNING_THRESHOLD && (
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
          <button onClick={() => handleSelectZona(alternativa)} className="w-full">
            <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
              <p className="font-bold text-slate-800 dark:text-slate-100">
                {getTituloZona(1)}: {alternativa.name}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                📍 {alternativa.referencia}
              </p>
              <FilaMetricas zona={alternativa} />
            </div>
          </button>
        )}

        {esTresOpciones && terceraOpcion && (
          <button onClick={() => handleSelectZona(terceraOpcion)} className="w-full">
            <div className="bg-white dark:bg-slate-800 border-2 border-blue-400 dark:border-blue-500 p-4 rounded-xl text-left">
              <p className="font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                <span>{terceraOpcion.name}</span>
                <NearestBadge visible={terceraOpcion.is_nearest} />
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                📍 {terceraOpcion.referencia}
              </p>
              <FilaMetricas zona={terceraOpcion} />
            </div>
          </button>
        )}

        {esTresOpciones && cuartaOpcion && (
          <button onClick={() => handleSelectZona(cuartaOpcion)} className="w-full">
            <div className="bg-white dark:bg-slate-800 border-2 border-emerald-400 dark:border-emerald-500 p-4 rounded-xl text-left">
              <p className="font-bold text-slate-800 dark:text-slate-100">
                {cuartaOpcion.name}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                📍 {cuartaOpcion.referencia}
              </p>
              <FilaMetricas zona={cuartaOpcion} />
            </div>
          </button>
        )}

        <InteractiveMap
          puntos={zonas
            .filter(z => z.lat != null && z.lng != null)
            .map(z => ({
              id: z.zone_id,
              nombre: z.name,
              lat: z.lat!,
              lng: z.lng!,
              referencia: z.referencia,
              tipo: 'estacionamiento',
              originalData: z
            })) as InteractiveMapPoint<ZonaEstacionamientoItem>[]}
          onSelectPunto={(p) => {
            // Todo punto se construyó con `originalData: z`, así que la ausencia
            // es defensiva. El cast anterior (`p as ZonaEstacionamientoItem`) lo
            // rechazaba TypeScript porque las dos formas no comparten ningún
            // miembro, y además descartaba el registro real.
            if (p.originalData) handleSelectZona(p.originalData)
          }}
          onUserLocationUpdate={() => {}}
        />

        {listaRestante.length > 0 && (
          <ZonaCardsList
            items={listaRestante}
            icon="🚗"
            label="zonas de estacionamiento disponibles"
            userLocation={userLocation}
            onSelect={(z) => handleSelectZona(z)}
          />
        )}

        {esTresOpciones && (
          <p className="text-xs text-slate-400 dark:text-slate-400 text-center pb-16">
            {getConfianzaLabel(principal?.confidence)}
          </p>
        )}
      </div>

{gpsPrompt}

      <AppFooter variant="public" />
    </div>
  )
}

export default Estacionar
