import { Info } from 'lucide-react'
import { getDistancias } from '@/utils/geo'

export interface ZonaBase {
  zone_id: string
  name: string
  estado: string | null
  saturation_level: number | null
  confidence: number | null
  estimated_wait: number | null
  availability: number | null
  is_nearest?: boolean
  lat: number | null
  lng: number | null
  referencia?: string
  distancia_min?: number | null
}

export const getEstadoStyles = (estado: string | null | undefined) => {
  if (!estado) return 'bg-gray-500/20 text-gray-500 dark:text-gray-300'
  switch (estado) {
    case 'bajo': return 'bg-success/20 text-success'
    case 'medio': return 'bg-warning/20 text-warning'
    case 'alto': return 'bg-danger/20 text-danger'
    case 'colapsado': return 'bg-gray-500/20 text-gray-500 dark:text-gray-300'
    default: return 'bg-gray-500/20 text-gray-500 dark:text-gray-300'
  }
}

export const getEstadoLabel = (estado: string | null | undefined): string => {
  if (!estado) return '—' // Fallback visual aprobado para zonas informativas
  switch (estado) {
    case 'bajo': return '🟢 Bajo'
    case 'medio': return '🟡 Medio'
    case 'alto': return '🔴 Alto'
    case 'colapsado': return '⚫ Colapsado'
    default: return estado
  }
}

export const getConfianzaLabel = (confidence: number | null | undefined): string => {
  if (confidence == null) return '❗ Disponibilidad incierta'
  if (confidence >= 0.7) return '✅ Alta probabilidad'
  if (confidence >= 0.4) return '⚠️ Últimos lugares'
  return '❗ Disponibilidad incierta'
}

const getConfianzaColor = (confidence: number | null | undefined): string => {
  if (confidence == null) return ''
  if (confidence >= 0.7) return 'text-green-600'
  if (confidence >= 0.4) return 'text-yellow-600'
  return 'text-red-600'
}

export const NearestBadge = ({ visible }: { visible?: boolean }) =>
  visible ? (
    <span className="px-2 py-1 rounded text-xs font-bold whitespace-nowrap bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
      ⭐ Más cercana
    </span>
  ) : null

interface ZonaCardsListProps<T extends ZonaBase> {
  items: T[]
  icon: string
  label: string
  userLocation: [number, number] | null
  onSelect: (zona: T) => void
}

export function ZonaCardsList<T extends ZonaBase>({
  items,
  icon,
  label,
  userLocation,
  onSelect,
}: ZonaCardsListProps<T>) {
  return (
    <div className="space-y-2 pb-16">
      <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 flex justify-between">
        <span>{icon} {items.length} {label}</span>
        {userLocation && <span className="text-blue-500 text-[10px] font-semibold">📡 Ubicación GPS activa</span>}
      </p>
      {items.map(zona => {
        const dist = getDistancias(zona.lat ?? 0, zona.lng ?? 0, userLocation, zona.distancia_min ?? 5)
        return (
          <button
            key={zona.zone_id}
            onClick={() => onSelect(zona)}
            className="w-full text-left bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors group shadow-sm flex items-start gap-2"
          >
            <span className="text-lg mt-0.5">{icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex justify-between items-center gap-2">
                <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">
                  {zona.name}
                </p>
                <span className="flex items-center gap-1.5 shrink-0">
                  <NearestBadge visible={zona.is_nearest} />
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getEstadoStyles(zona.estado)}`}>
                    {getEstadoLabel(zona.estado)}
                  </span>
                </span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 flex flex-wrap gap-x-2 gap-y-0.5 items-center">
                <span>🚶 {dist.walking}</span>
                <span className="opacity-50">·</span>
                <span>🚗 {dist.driving}</span>
                {zona.saturation_level != null && (
                  <>
                    <span className="opacity-50">·</span>
                    <span>📊 {Math.round((1 - zona.saturation_level) * 100)}% de posibilidad</span>
                  </>
                )}
                {zona.estimated_wait != null && (
                  <>
                    <span className="opacity-50">·</span>
                    <span>⏱️ {zona.estimated_wait} min espera</span>
                  </>
                )}
                <span className="opacity-50">·</span>
                <span className={getConfianzaColor(zona.confidence)}>
                  {getConfianzaLabel(zona.confidence)}
                </span>
              </p>
            </div>
            <Info size={16} className="text-slate-400 flex-shrink-0" />
          </button>
        )
      })}
    </div>
  )
}
