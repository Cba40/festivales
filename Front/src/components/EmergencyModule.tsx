import { useCallback, useEffect, useState } from 'react'
import {
  AlertTriangle,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Info,
  Loader2,
  MapPin,
  Phone,
  PhoneCall,
  X,
} from 'lucide-react'
import {
  getCities,
  getEmergencies,
  getProtocols,
  getRecommendedResource,
  useEmergencyRecommendations,
  type EmergencyItem,
  type EmergencyType,
  type ProtocolContext,
  type ProtocolDTO,
} from '@/services/emergencyProduct'
import { useAppStore } from '@/core/state/store'
import { InteractiveMap, type InteractiveMapPoint } from '@/components/InteractiveMap'

interface EmergencyModuleProps {
  context: ProtocolContext
  cityId?: string
}

// Mapeo de tipos de emergencia → tipos de marcador del mapa interactivo
// ('salud_emergencia' evita colisión con el servicio 'salud' del mapa de Servicios).
const TIPO_MAPA: Record<EmergencyType, string> = {
  policia: 'policia',
  bomberos: 'bomberos',
  salud: 'salud_emergencia',
  defensa_civil: 'defensa_civil',
  numero_emergencia: 'numero_emergencia',
  otro: 'otro',
}

const TYPE_LABEL: Record<EmergencyType, string> = {
  policia: 'Policía',
  bomberos: 'Bomberos',
  salud: 'Salud',
  defensa_civil: 'Defensa Civil',
  numero_emergencia: 'Emergencia',
  otro: 'Otro',
}

const TYPE_BADGE: Record<EmergencyType, string> = {
  policia: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  bomberos: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  salud: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  defensa_civil:
    'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  numero_emergencia:
    'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  otro: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
}

const handleMaps = (lat: number, lng: number) => {
  window.open(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`, '_blank')
}

export const EmergencyModule = ({ context, cityId }: EmergencyModuleProps) => {
  const [resolvedCityId, setResolvedCityId] = useState<string | null>(cityId ?? null)
  const [resolvingCity, setResolvingCity] = useState(false)
  const [cityError, setCityError] = useState<string | null>(null)
  const [cityAttempt, setCityAttempt] = useState(0)

  const [protocols, setProtocols] = useState<ProtocolDTO[] | null>(null)
  const [protocolsError, setProtocolsError] = useState<string | null>(null)
  const [protocolsAttempt, setProtocolsAttempt] = useState(0)

  const [selectedProtocol, setSelectedProtocol] = useState<ProtocolDTO | null>(null)
  const [recommendedResource, setRecommendedResource] =
    useState<EmergencyItem | null>(null)
  const [resourceLoading, setResourceLoading] = useState(false)
  const [resourceError, setResourceError] = useState<string | null>(null)
  const [showTerritorial, setShowTerritorial] = useState(false)
  const [selectedResource, setSelectedResource] = useState<EmergencyItem | null>(null)

  const userLocation = useAppStore(s => s.userLocation)

  // Auto-descubrimiento: si no se provee cityId explícito, se resuelve la
  // primera ciudad disponible para el módulo público (sin config externa).
  useEffect(() => {
    let cancelled = false

    if (cityId) {
      setResolvedCityId(cityId)
      setCityError(null)
      setResolvingCity(false)
      return
    }

    setResolvingCity(true)
    setCityError(null)
    ;(async () => {
      try {
        const cities = await getCities()
        if (cancelled) return
        if (cities.length === 0) {
          setResolvedCityId(null)
          setCityError('No hay ciudades configuradas')
        } else {
          // Auto-descubrimiento con datos: se elige la primera ciudad que
          // realmente tenga emergencias registradas, en el orden del backend.
          const ciudadConDatos = (
            await Promise.all(
              cities.map(async (c) => {
                try {
                  const res = await getEmergencies(c.id, 1)
                  return res.emergencies.length > 0 ? c : null
                } catch {
                  return null
                }
              })
            )
          ).find((c) => c !== null)
          setResolvedCityId((ciudadConDatos ?? cities[0]).id)
          setCityError(null)
        }
      } catch {
        if (cancelled) return
        setResolvedCityId(null)
        setCityError('No se pudieron cargar las ciudades')
      } finally {
        if (!cancelled) setResolvingCity(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [cityId, cityAttempt])

  // Carga de protocolos del contexto elegido.
  useEffect(() => {
    let cancelled = false
    setProtocols(null)
    setProtocolsError(null)
    ;(async () => {
      try {
        const list = await getProtocols(context)
        if (!cancelled) setProtocols(list)
      } catch {
        if (!cancelled) setProtocolsError('No se pudieron cargar los protocolos')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [context, protocolsAttempt])

  // Geolocalización opcional: se intenta pedir el permiso una sola vez al
  // montar el módulo. Si se niega o no hay GPS, todo sigue funcionando.
  useEffect(() => {
    if (!('geolocation' in navigator)) return
    if (useAppStore.getState().userLocation !== null) return
    useAppStore.getState().requestLocation()
  }, [])

  const retryCities = useCallback(() => {
    setCityAttempt(a => a + 1)
  }, [])

  const retryProtocols = useCallback(() => {
    setProtocolsAttempt(a => a + 1)
  }, [])

  const effectiveCityId = resolvedCityId ?? cityId
  const { data, loading, error, refresh } =
    useEmergencyRecommendations(effectiveCityId)

  useEffect(() => {
    refresh()
  }, [refresh])

  // Resolución del recurso territorial recomendado (S3) cuando el protocolo
  // elegido declara target_type y ya conocemos la ciudad.
  const targetType = selectedProtocol?.target_type ?? null
  const canResolve = targetType !== null && effectiveCityId !== null

  useEffect(() => {
    if (!canResolve) {
      setRecommendedResource(null)
      setResourceError(null)
      setResourceLoading(false)
      return
    }

    let cancelled = false
    setResourceLoading(true)
    setResourceError(null)

    ;(async () => {
      try {
        const lat = userLocation?.[0]
        const lng = userLocation?.[1]
        const resource = await getRecommendedResource(
          targetType,
          effectiveCityId as string,
          lat,
          lng
        )
        if (cancelled) return
        setRecommendedResource(resource)
      } catch {
        if (cancelled) return
        setRecommendedResource(null)
        setResourceError('No se pudo obtener el recurso recomendado')
      } finally {
        if (!cancelled) setResourceLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [canResolve, targetType, effectiveCityId, userLocation])

  const backToList = useCallback(() => {
    setSelectedProtocol(null)
    setRecommendedResource(null)
    setResourceError(null)
    setResourceLoading(false)
    setShowTerritorial(false)
  }, [])

  const all = data?.emergencies ?? []
  // Registros sin ubicación física (911, 107, 100): siempre destacados.
  const numerosEmergencia = all.filter(e => e.type === 'numero_emergencia')
  const rest = all.filter(e => e.type !== 'numero_emergencia')

  if (resolvingCity) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-slate-500 dark:text-slate-300 gap-2">
        <Loader2 size={28} className="animate-spin" />
        <p className="text-sm font-semibold">Cargando ubicación...</p>
      </div>
    )
  }

  if (cityError) {
    return (
      <div className="flex flex-col items-center justify-center p-8 space-y-3">
        <p className="text-danger font-bold flex items-center gap-2">
          <AlertTriangle size={18} /> Error al cargar
        </p>
        <p className="text-sm text-slate-500 text-center">{cityError}</p>
        <button
          onClick={retryCities}
          className="bg-primary text-white px-6 py-2 rounded-lg font-bold active:scale-95 transition-transform"
        >
          Reintentar
        </button>
      </div>
    )
  }

  if (protocols === null && !protocolsError) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-slate-500 dark:text-slate-300 gap-2">
        <Loader2 size={28} className="animate-spin" />
        <p className="text-sm font-semibold">Cargando protocolos...</p>
      </div>
    )
  }

  if (protocolsError) {
    return (
      <div className="flex flex-col items-center justify-center p-8 space-y-3">
        <p className="text-danger font-bold flex items-center gap-2">
          <AlertTriangle size={18} /> Error al cargar
        </p>
        <p className="text-sm text-slate-500 text-center">{protocolsError}</p>
        <button
          onClick={retryProtocols}
          className="bg-primary text-white px-6 py-2 rounded-lg font-bold active:scale-95 transition-transform"
        >
          Reintentar
        </button>
      </div>
    )
  }

  if (protocols.length === 0) {
    return (
      <div className="text-center text-slate-500 dark:text-slate-300 py-10">
        No hay protocolos disponibles para esta sección.
      </div>
    )
  }

  if (selectedProtocol) {
    return (
      <>
      <div className="space-y-4">
        <EmergencyMapSection
          emergencies={all}
          typeFilter={selectedProtocol.target_type}
          recomendadoId={recommendedResource?.id ?? null}
          onSelect={setSelectedResource}
        />

        <button
          onClick={backToList}
          className="flex items-center gap-1 text-primary font-bold text-sm active:scale-95 transition-transform"
        >
          <ChevronLeft size={18} /> Volver
        </button>

        {/* Detalle del protocolo */}
        <div className="bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{selectedProtocol.icon}</span>
            <h2 className="font-black text-lg text-slate-800 dark:text-slate-100 leading-tight">
              {selectedProtocol.title}
            </h2>
          </div>
          {selectedProtocol.description && (
            <p className="text-sm text-slate-600 dark:text-slate-300">
              {selectedProtocol.description}
            </p>
          )}
          <ol className="space-y-2">
            {selectedProtocol.steps.map((step, i) => (
              <li key={i} className="flex gap-2 items-start">
                <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-black">
                  {i + 1}
                </span>
                <p className="text-sm text-slate-700 dark:text-slate-200">{step}</p>
              </li>
            ))}
          </ol>
        </div>

        {/* Recurso recomendado (S3) */}
        {targetType !== null && (
          <RecommendedResourceBlock
            loading={resourceLoading}
            error={resourceError}
            resource={recommendedResource}
            onMaps={handleMaps}
          />
        )}

        {/* Ayuda territorial cercana (lista de emergencias de la ciudad) */}
        <div className="pt-1">
          <button
            onClick={() => setShowTerritorial(v => !v)}
            className="w-full flex items-center justify-between bg-white dark:bg-slate-800 p-3 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm active:scale-[0.98] transition-transform"
          >
            <span className="font-bold text-slate-800 dark:text-slate-100 text-sm">
              Ayuda territorial cercana
            </span>
            {showTerritorial ? (
              <ChevronUp size={18} className="text-slate-400" />
            ) : (
              <ChevronDown size={18} className="text-slate-400" />
            )}
          </button>

          {showTerritorial && (
            <div className="space-y-3 mt-3">
              {loading ? (
                <div className="flex items-center justify-center gap-2 p-4 text-slate-500 text-sm">
                  <Loader2 size={16} className="animate-spin" /> Cargando recursos...
                </div>
              ) : error ? (
                <div className="flex flex-col items-center gap-2 p-4">
                  <p className="text-danger text-sm font-bold flex items-center gap-1.5">
                    <AlertTriangle size={16} /> {error}
                  </p>
                  <button
                    onClick={() => refresh()}
                    className="bg-primary text-white px-5 py-2 rounded-lg font-bold text-sm active:scale-95 transition-transform"
                  >
                    Reintentar
                  </button>
                </div>
              ) : all.length === 0 ? (
                <div className="text-center text-slate-500 dark:text-slate-300 py-6 text-sm">
                  No hay recursos registrados en esta ciudad.
                </div>
              ) : (
                <>
                  {numerosEmergencia.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-xs font-bold text-red-600 dark:text-red-400 uppercase tracking-wide flex items-center gap-1.5">
                        <PhoneCall size={14} /> Llamadas de emergencia
                      </p>
                      {numerosEmergencia.map(e => (
                        <div
                          key={e.id}
                          className="rounded-2xl p-4 bg-red-600 text-white shadow-lg shadow-red-600/30 border-2 border-red-500 flex flex-col gap-3"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div>
                              <p className="font-black text-lg leading-tight">
                                {e.name}
                              </p>
                              <p className="text-xs text-red-100">
                                {e.services || 'Servicio de emergencias'}
                              </p>
                            </div>
                            <span className="px-2 py-1 rounded-full bg-white/20 text-[10px] font-bold uppercase">
                              {e.emergency_number
                                ? `Nro ${e.emergency_number}`
                                : 'Gratuito'}
                            </span>
                          </div>
                          <a
                            href={`tel:${e.phone || (e.emergency_number ? `*${e.emergency_number}` : '')}`}
                            className="flex-1 flex items-center justify-center gap-2 bg-white text-red-600 font-black py-3 rounded-xl text-base transition-transform active:scale-95"
                          >
                            <PhoneCall size={20} /> Llamar al{' '}
                            {e.emergency_number || e.phone || e.name}
                          </a>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="space-y-3">
                    {rest.map(e => (
                      <EmergencyCard key={e.id} emergency={e} />
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      <ResourceBottomSheet
        resource={selectedResource}
        onClose={() => setSelectedResource(null)}
      />
      </>
    )
  }

  // Vista inicial: lista de protocolos del contexto.
  return (
    <div className="space-y-4">
      <EmergencyMapSection
        emergencies={all}
        typeFilter={null}
        recomendadoId={null}
        onSelect={setSelectedResource}
      />

      <p className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
        ¿Qué necesitás hacer? Elegí una opción
      </p>
      <div className="space-y-2">
        {protocols.map(p => (
          <button
            key={p.id}
            onClick={() => {
              setSelectedProtocol(p)
              setShowTerritorial(false)
            }}
            className="w-full flex items-center gap-3 bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm hover:border-blue-400 dark:hover:border-blue-500 transition-colors active:scale-[0.98]"
          >
            <span className="text-2xl">{p.icon}</span>
            <span className="font-bold text-slate-800 dark:text-slate-100 text-left">
              {p.title}
            </span>
            <ChevronRight size={18} className="ml-auto flex-shrink-0 text-slate-400" />
          </button>
        ))}
      </div>

      <ResourceBottomSheet
        resource={selectedResource}
        onClose={() => setSelectedResource(null)}
      />
    </div>
  )
}

interface EmergencyMapSectionProps {
  emergencies: EmergencyItem[]
  typeFilter: EmergencyType | null
  recomendadoId: string | null
  onSelect: (e: EmergencyItem) => void
}

const EmergencyMapSection = ({
  emergencies,
  typeFilter,
  recomendadoId,
  onSelect,
}: EmergencyMapSectionProps) => {
  const visibles =
    typeFilter === null
      ? emergencies
      : emergencies.filter(e => e.type === typeFilter)

  const puntos: InteractiveMapPoint[] = visibles
    .filter(e => e.latitude != null && e.longitude != null)
    .map(e => ({
      id: e.id,
      tipo: TIPO_MAPA[e.type],
      nombre: e.name,
      lat: e.latitude!,
      lng: e.longitude!,
      referencia: e.reference ?? undefined,
      originalData: e,
    }))

  return (
    <div className="rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-700 shadow-sm">
      <InteractiveMap
        puntos={puntos}
        onSelectPunto={(p) => onSelect(p as EmergencyItem)}
        onUserLocationUpdate={() => {}}
        puntoResaltadoId={
          recomendadoId != null && puntos.some(p => p.id === recomendadoId)
            ? recomendadoId
            : null
        }
      />
    </div>
  )
}

const ResourceBottomSheet = ({
  resource,
  onClose,
}: {
  resource: EmergencyItem | null
  onClose: () => void
}) => {
  if (!resource) return null

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-[9999]" onClick={onClose} />
      <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl">
        <div
          className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
          onClick={onClose}
        />
        <div className="flex items-center justify-between gap-2 mb-2">
          <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">
            {resource.name}
          </h3>
          <span
            className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${TYPE_BADGE[resource.type]}`}
          >
            {TYPE_LABEL[resource.type]}
          </span>
        </div>
        <div className="space-y-2 mb-4 text-sm text-slate-600 dark:text-slate-300">
          {resource.address && (
            <p className="flex items-start gap-1.5">
              <MapPin size={16} className="flex-shrink-0 mt-0.5" /> {resource.address}
            </p>
          )}
          {resource.reference && (
            <p className="flex items-start gap-1.5">
              <Info size={16} className="flex-shrink-0 mt-0.5" /> {resource.reference}
            </p>
          )}
          {resource.services && <p>🛟 {resource.services}</p>}
          {resource.schedule != null && <p>🕐 {resource.schedule}</p>}
          {resource.distance_km != null && (
            <p>📍 A {resource.distance_km.toFixed(1)} km de tu ubicación</p>
          )}
        </div>
        <div className="flex flex-col gap-2">
          {resource.phone && (
            <a
              href={`tel:${resource.phone}`}
              className="w-full bg-primary text-white py-3 rounded-xl font-bold flex items-center justify-center gap-2 active:scale-95 transition-transform"
            >
              <Phone size={18} /> Llamar
            </a>
          )}
          {resource.latitude != null && resource.longitude != null && (
            <button
              onClick={() => handleMaps(resource.latitude!, resource.longitude!)}
              className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold flex items-center justify-center gap-2 active:scale-95 transition-transform"
            >
              <MapPin size={18} /> Iniciar ruta
            </button>
          )}
          <button
            onClick={onClose}
            className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold flex items-center justify-center gap-2"
          >
            <X size={16} /> Cerrar
          </button>
        </div>
      </div>
    </>
  )
}

const RecommendedResourceBlock = ({
  loading,
  error,
  resource,
  onMaps,
}: {
  loading: boolean
  error: string | null
  resource: EmergencyItem | null
  onMaps: (lat: number, lng: number) => void
}) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm text-slate-500 text-sm">
        <Loader2 size={16} className="animate-spin" /> Buscando ayuda cercana...
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-2 bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
        <p className="text-danger text-sm font-bold flex items-center gap-1.5">
          <AlertTriangle size={16} /> {error}
        </p>
      </div>
    )
  }

  if (!resource) {
    return (
      <div className="text-center bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm text-sm text-slate-500 dark:text-slate-300">
        No hay un recurso territorial recomendado para esta emergencia en la
        ciudad.
      </div>
    )
  }

  const hasLocation = resource.latitude != null && resource.longitude != null

  return (
    <div className="rounded-2xl p-4 bg-primary text-white shadow-lg shadow-primary/30 border-2 border-primary flex flex-col gap-3">
      <p className="text-xs font-bold uppercase tracking-wide text-white/80">
        Recurso recomendado
      </p>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-black text-lg leading-tight truncate">{resource.name}</p>
          {resource.address && <p className="text-xs text-white/70 truncate">{resource.address}</p>}
        </div>
        {resource.distance_km != null && (
          <span className="flex-shrink-0 text-xs font-bold bg-white/20 rounded-full px-2 py-1">
            📍 {resource.distance_km.toFixed(1)} km
          </span>
        )}
      </div>

      {resource.phone ? (
        <a
          href={`tel:${resource.phone}`}
          className="flex items-center justify-center gap-2 bg-white text-primary font-black py-3 rounded-xl text-base transition-transform active:scale-95"
        >
          <Phone size={20} /> Contactar {TYPE_LABEL[resource.type]}
        </a>
      ) : hasLocation ? (
        <button
          onClick={() => onMaps(resource.latitude!, resource.longitude!)}
          className="flex items-center justify-center gap-2 bg-white text-primary font-black py-3 rounded-xl text-base transition-transform active:scale-95"
        >
          <MapPin size={20} /> Cómo llegar
        </button>
      ) : (
        <div className="text-center text-white/80 text-sm font-bold py-2">
          Sin contacto registrado
        </div>
      )}
    </div>
  )
}

const EmergencyCard = ({ emergency: e }: { emergency: EmergencyItem }) => {
  const hasLocation = e.latitude != null && e.longitude != null

  return (
    <div className="bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-bold text-slate-800 dark:text-slate-100 truncate">
            {e.name}
          </p>
          <span className={`inline-block px-2 py-0.5 mt-1 rounded text-[10px] font-bold ${TYPE_BADGE[e.type]}`}>
            {TYPE_LABEL[e.type].toUpperCase()}
          </span>
        </div>
        {e.distance_km != null && (
          <span className="flex-shrink-0 text-xs font-bold text-primary bg-primary/10 rounded-full px-2 py-1">
            📍 {e.distance_km.toFixed(1)} km
          </span>
        )}
      </div>

      {(e.address || e.reference) && (
        <div className="text-xs text-slate-500 dark:text-slate-400 space-y-0.5">
          {e.address && <p className="truncate">📍 {e.address}</p>}
          {e.reference && <p className="truncate">🗺️ {e.reference}</p>}
        </div>
      )}

      {e.schedule && (
        <p className="text-xs text-slate-400 dark:text-slate-500">🕐 {e.schedule}</p>
      )}

      <div className="flex gap-2 pt-1">
        {e.phone && (
          <a
            href={`tel:${e.phone}`}
            className="flex-1 flex items-center justify-center gap-1 bg-success/15 dark:bg-success/25 hover:bg-success/25 dark:hover:bg-success/35 text-success font-bold py-2.5 rounded-xl text-sm transition-colors active:scale-95"
          >
            <Phone size={16} /> Llamar
          </a>
        )}
        {hasLocation && (
          <button
            onClick={() => handleMaps(e.latitude!, e.longitude!)}
            className="flex-1 flex items-center justify-center gap-1 bg-primary text-white hover:bg-primary/90 py-2.5 rounded-xl font-bold text-sm transition-colors shadow-lg shadow-primary/25 active:scale-95"
          >
            <MapPin size={16} /> Cómo llegar
          </button>
        )}
      </div>
    </div>
  )
}

export default EmergencyModule