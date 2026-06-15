import { Dot, Info } from 'lucide-react'
import type { PuntoServicioMapa } from '@/data/mappers'
import { formatUpdatedAt } from '@/utils/formatTime'

interface SimpleMapProps {
  puntos: PuntoServicioMapa[]
  onSelectPunto: (punto: PuntoServicioMapa) => void
}

export const SimpleMap = ({ puntos, onSelectPunto }: SimpleMapProps) => {
  const getColor = (tipo: string) => {
    switch (tipo) {
      case 'banos': return 'bg-blue-500 shadow-blue-500/50'
      case 'hidratacion': return 'bg-cyan-500 shadow-cyan-500/50'
      case 'descanso': return 'bg-green-500 shadow-green-500/50'
      case 'salud': return 'bg-red-500 shadow-red-500/50'
      default: return 'bg-gray-500 shadow-gray-500/50'
    }
  }

  const getLabel = (tipo: string) => {
    switch (tipo) {
      case 'banos': return '🚻'
      case 'hidratacion': return '💧'
      case 'descanso': return '🪑'
      case 'salud': return '🏥'
      default: return '📍'
    }
  }

  return (
    <div className="space-y-3">
      {/* Mapa visual simple */}
      <div className="w-full bg-white dark:bg-slate-800 rounded-xl border-2 border-slate-200 dark:border-slate-700 aspect-square relative overflow-hidden shadow-md">
        {/* Grid opcional de referencia (sutil) */}
        <div className="absolute inset-0 opacity-10">
          {[...Array(5)].map((_, i) => (
            <div
              key={`h-${i}`}
              className="absolute border-b border-slate-300 dark:border-slate-600 w-full"
              style={{ top: `${(i + 1) * 20}%` }}
            />
          ))}
          {[...Array(5)].map((_, i) => (
            <div
              key={`v-${i}`}
              className="absolute border-r border-slate-300 dark:border-slate-600 h-full"
              style={{ left: `${(i + 1) * 20}%` }}
            />
          ))}
        </div>

        {/* Puntos del mapa */}
        {puntos.map(punto => (
          <button
            key={punto.id}
            onClick={() => onSelectPunto(punto)}
            className="absolute transform -translate-x-1/2 -translate-y-1/2 group z-10"
            style={{ left: `${punto.x}%`, top: `${punto.y}%` }}
            title={punto.nombre}
          >
            {/* Aura de glow */}
            <div className={`absolute -inset-2 rounded-full ${getColor(punto.tipo)} opacity-30 group-hover:opacity-50 transition-opacity blur-md`} />
            
            {/* Punto principal */}
            <div className={`relative w-8 h-8 rounded-full ${getColor(punto.tipo)} shadow-lg group-hover:scale-110 transition-transform flex items-center justify-center text-white font-bold text-sm border-2 border-white dark:border-slate-800`}>
              {getLabel(punto.tipo)}
            </div>
          </button>
        ))}
      </div>

      {/* Lista de puntos para referencia rápida */}
      <div className="space-y-2">
        <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1">
          📍 {puntos.length} puntos disponibles
        </p>
        {puntos.map(punto => (
          <button
            key={punto.id}
            onClick={() => onSelectPunto(punto)}
            className="w-full text-left bg-slate-50 dark:bg-slate-800/50 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors group"
          >
            <div className="flex items-start gap-2">
              <span className="text-lg mt-0.5">{getLabel(punto.tipo)}</span>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                  {punto.nombre}
                </p>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">
                  🚶 {punto.distancia} min
                </p>
              </div>
              <Info size={16} className="text-slate-400 flex-shrink-0" />
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
