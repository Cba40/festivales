import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, Loader2, MapPin, Phone, PhoneCall } from 'lucide-react'
import {
  getCities,
  useEmergencyRecommendations,
  type EmergencyItem,
  type EmergencyType,
} from '@/services/emergencyProduct'

type CategoryKey = 'todos' | 'policia' | 'bomberos' | 'salud' | 'defensa_civil'

interface EmergencyModuleProps {
  cityId?: string
  defaultType?: EmergencyType
}

const CATEGORIAS: Array<{ key: CategoryKey; label: string; emoji: string }> = [
  { key: 'todos', label: 'Todos', emoji: '📋' },
  { key: 'policia', label: 'Policía', emoji: '👮' },
  { key: 'bomberos', label: 'Bomberos', emoji: '🚒' },
  { key: 'salud', label: 'Salud', emoji: '🚑' },
  { key: 'defensa_civil', label: 'Defensa Civil', emoji: '🛡️' },
]

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

export const EmergencyModule = ({ cityId, defaultType }: EmergencyModuleProps) => {
  const [resolvedCityId, setResolvedCityId] = useState<string | null>(cityId ?? null)
  const [resolvingCity, setResolvingCity] = useState(false)
  const [cityError, setCityError] = useState<string | null>(null)
  const [cityAttempt, setCityAttempt] = useState(0)

  const [activeType, setActiveType] = useState<CategoryKey>(
    defaultType && defaultType !== 'otro' && defaultType !== 'numero_emergencia'
      ? (defaultType as CategoryKey)
      : 'todos'
  )

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
          setResolvedCityId(cities[0].id)
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

  const retryCities = useCallback(() => {
    setCityAttempt(a => a + 1)
  }, [])

  const effectiveCityId = resolvedCityId ?? cityId
  const { data, loading, error, refresh } =
    useEmergencyRecommendations(effectiveCityId)

  useEffect(() => {
    refresh()
  }, [refresh])

  const all = data?.emergencies ?? []
  // Registros sin ubicación física (911, 107, 100): siempre destacados al principio.
  const numerosEmergencia = all.filter(e => e.type === 'numero_emergencia')
  const rest = all.filter(e => e.type !== 'numero_emergencia')
  const filtered =
    activeType === 'todos' ? rest : rest.filter(e => e.type === activeType)

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

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-slate-500 dark:text-slate-300 gap-2">
        <Loader2 size={28} className="animate-spin" />
        <p className="text-sm font-semibold">Cargando emergencias...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-8 space-y-3">
        <p className="text-danger font-bold flex items-center gap-2">
          <AlertTriangle size={18} /> Error al cargar
        </p>
        <p className="text-sm text-slate-500 text-center">{error}</p>
        <button
          onClick={() => refresh()}
          className="bg-primary text-white px-6 py-2 rounded-lg font-bold active:scale-95 transition-transform"
        >
          Reintentar
        </button>
      </div>
    )
  }

  if (all.length === 0) {
    return (
      <div className="text-center text-slate-500 dark:text-slate-300 py-10">
        No hay emergencias registradas para esta ciudad.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Bloque superior fijo: números de emergencia sin ubicación física */}
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
                  <p className="font-black text-lg leading-tight">{e.name}</p>
                  <p className="text-xs text-red-100">
                    {e.services || 'Servicio de emergencias'}
                  </p>
                </div>
                <span className="px-2 py-1 rounded-full bg-white/20 text-[10px] font-bold uppercase">
                  {e.emergency_number ? `Nro ${e.emergency_number}` : 'Gratuito'}
                </span>
              </div>
              <a
                href={`tel:${e.phone || (e.emergency_number ? `*${e.emergency_number}` : '')}`}
                className="flex-1 flex items-center justify-center gap-2 bg-white text-red-600 font-black py-3 rounded-xl text-base transition-transform active:scale-95"
              >
                <PhoneCall size={20} /> Llamar al {e.emergency_number || e.phone || e.name}
              </a>
            </div>
          ))}
        </div>
      )}

      {/* Selector de categoría */}
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
        {CATEGORIAS.map(cat => {
          const activa = activeType === cat.key
          return (
            <button
              key={cat.key}
              onClick={() => setActiveType(cat.key)}
              className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl border-2 font-bold text-sm transition-transform active:scale-95 ${
                activa
                  ? 'bg-primary text-white border-primary shadow-lg shadow-primary/25'
                  : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500'
              }`}
            >
              <span>{cat.emoji}</span>
              <span>{cat.label}</span>
            </button>
          )
        })}
      </div>

      {/* Lista de resultados */}
      {filtered.length === 0 ? (
        <div className="text-center text-slate-500 dark:text-slate-300 py-8">
          No hay emergencias de esta categoría.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(e => (
            <EmergencyCard key={e.id} emergency={e} />
          ))}
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
