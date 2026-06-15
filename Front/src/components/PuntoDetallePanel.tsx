import { createPortal } from 'react-dom'
import { Map, X, UtensilsCrossed } from 'lucide-react'
import type { PuntoComida } from '@/data/mappers'
import { getConfianza, getConfianzaLabel } from '@/utils/confianza'
import { formatUpdatedAt } from '@/utils/formatTime'

const getCategoriaLabel = (cat: string) => {
  switch (cat) {
    case 'rapido': return 'Comida rápida'
    case 'comida': return 'Comida completa'
    case 'bebida': return 'Bebidas'
    default: return cat
  }
}

const getDestCoords = (p: PuntoComida): [number, number] | null => {
  if (p.geometryType === 'line') {
    const c = p.coordinates as [number, number][]
    if (Array.isArray(c[0]) && typeof c[0][0] === 'number' && typeof c[0][1] === 'number') return [c[0][0], c[0][1]]
  }
  const c = p.coordinates as [number, number]
  if (typeof c[0] === 'number' && typeof c[1] === 'number') return [c[0], c[1]]
  if (p.lat && p.lng) return [p.lat, p.lng]
  return null
}

interface PuntoDetallePanelProps {
  punto: PuntoComida | null
  onClose: () => void
}

const PuntoDetallePanel = ({ punto, onClose }: PuntoDetallePanelProps) => {
  if (!punto) return null

  const dest = getDestCoords(punto)
  const gmapsUrl = dest ? `https://www.google.com/maps/dir/?api=1&destination=${dest[0]},${dest[1]}` : '#'

  return createPortal(
    <>
      <div
        className="fixed inset-0 bg-black/50 z-[9998]"
        onClick={onClose}
      />
      <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[9999] max-w-md mx-auto shadow-2xl">
        <div
          className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
          onClick={onClose}
        />

        <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
          {punto.nombre}
        </h3>

        <div className="space-y-2 mb-4">
          <p className="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-1">
            <UtensilsCrossed size={16} /> {getCategoriaLabel(punto.categoria)}
          </p>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            📍 {punto.referencia}
          </p>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            🚶 {punto.distancia_min} min
          </p>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            ⏱️ Espera: {punto.espera_min} min
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {formatUpdatedAt(punto.updatedAt)}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-300">
            {getConfianzaLabel(getConfianza(punto.estado))}
          </p>
        </div>

        {dest && (
          <a
            href={gmapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2"
          >
            <Map size={20} />
            Iniciar ruta
          </a>
        )}

        <button
          onClick={onClose}
          className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold transition-transform active:scale-95 flex items-center justify-center gap-2"
        >
          <X size={16} />
          Cerrar
        </button>
      </div>
    </>,
    document.body
  )
}

export default PuntoDetallePanel
