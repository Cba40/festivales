import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { SimpleMap } from '@/components/SimpleMap'
import { X } from 'lucide-react'
import { getServiciosMapPorTipo, type PuntoServicioMapa } from '@/data/mockServiciosMap'
import { formatUpdatedAt } from '@/utils/formatTime'

const opciones = [
  { emoji: '🚻', label: 'Baños', subtipo: 'banos' },
  { emoji: '💧', label: 'Agua', subtipo: 'hidratacion' },
  { emoji: '🪑', label: 'Descanso', subtipo: 'descanso' },
  { emoji: '🏥', label: 'Salud', subtipo: 'salud' }
]

const ServiciosGenerales = () => {
  const navigate = useNavigate()
  const [selected, setSelected] = useState<PuntoServicioMapa | null>(null)
  const [subtipoActivo, setSubtipoActivo] = useState<string | null>(null)

  const puntos = subtipoActivo ? getServiciosMapPorTipo(subtipoActivo as 'banos' | 'hidratacion' | 'descanso' | 'salud') : []

  const seleccionar = (subtipo: string) => {
    setSubtipoActivo(subtipo)
  }

  if (!subtipoActivo) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Más servicios" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4">
          <div className="grid grid-cols-1 min-[350px]:grid-cols-2 gap-3">
            {opciones.map(op => (
              <button
                key={op.subtipo}
                onClick={() => seleccionar(op.subtipo)}
                className="bg-white dark:bg-slate-800 p-6 rounded-xl text-center shadow-md hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
              >
                <p className="text-3xl mb-2">{op.emoji}</p>
                <p className="font-bold text-slate-800 dark:text-slate-100">{op.label}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title={opciones.find(o => o.subtipo === subtipoActivo)?.label || 'Servicios'} showBack onBack={() => setSubtipoActivo(null)} />

      <div className="flex-1 p-4 overflow-y-auto">
        <SimpleMap puntos={puntos} onSelectPunto={setSelected} />
      </div>

      {/* Bottom Sheet */}
      {selected && (
        <>
          <div className="fixed inset-0 bg-black/50 z-40" onClick={() => setSelected(null)} />
          <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
            <div className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer" onClick={() => setSelected(null)} />
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">{selected.nombre}</h3>
            <div className="space-y-2 mb-4">
              <p className="text-sm text-slate-600 dark:text-slate-300">📍 {selected.referencia}</p>
              <p className="text-sm text-slate-600 dark:text-slate-300">🚶 {selected.distancia} min caminando</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">{formatUpdatedAt(selected.updatedAt)}</p>
            </div>
            <button onClick={() => setSelected(null)} className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold flex items-center justify-center gap-2"><X size={16} /> Cerrar</button>
          </div>
        </>
      )}
    </div>
  )
}

export default ServiciosGenerales
