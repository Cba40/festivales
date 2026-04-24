import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Map, X } from 'lucide-react'
import {
  getServicioMasCercano,
  getSegundoMasCercano
} from '@/utils/servicios'
import { formatUpdatedAt } from '@/utils/formatTime'

type Servicio = {
  id: string
  nombre: string
  subtipo: string
  lat: number
  lng: number
  referencia: string
  distancia_min: number
  updatedAt: number
}

const opciones = [
  { emoji: '🚻', label: 'Baños', subtipo: 'banos' },
  { emoji: '💧', label: 'Agua', subtipo: 'hidratacion' },
  { emoji: '🪑', label: 'Descanso', subtipo: 'descanso' },
  { emoji: '🏥', label: 'Salud', subtipo: 'salud' }
]

const ServiciosGenerales = () => {
  const navigate = useNavigate()
  const [selected, setSelected] = useState<Servicio | null>(null)
  const [subtipoActivo, setSubtipoActivo] = useState<string | null>(null)

  const principal = subtipoActivo ? getServicioMasCercano(subtipoActivo) as Servicio | null : null
  const segundo = subtipoActivo ? getSegundoMasCercano(subtipoActivo) as Servicio | null : null
  const alternativa = segundo && segundo.distancia_min < 5 ? segundo : null

  const abrirMapa = (svc: Servicio) => {
    if (svc.lat && svc.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${svc.lat},${svc.lng}`,
        '_blank'
      )
    }
    setSelected(null)
  }

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

      <div className="flex-1 p-4 space-y-4">
        {principal && (
          <button
            onClick={() => setSelected(principal)}
            className="w-full"
          >
            <div className="bg-primary text-white p-6 rounded-xl text-left shadow-lg">
              <p className="text-lg font-bold">
                👉 {principal.nombre}
              </p>
              <p className="text-sm opacity-90 mt-2">📍 {principal.referencia}</p>
              <p className="text-sm opacity-90">🚶 {principal.distancia_min} min</p>
            </div>
          </button>
        )}

        {alternativa && (
          <button
            onClick={() => setSelected(alternativa)}
            className="w-full"
          >
            <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
              <p className="font-bold text-slate-800 dark:text-slate-100">
                Alternativa: {alternativa.nombre}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                📍 {alternativa.referencia}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                🚶 {alternativa.distancia_min} min
              </p>
            </div>
          </button>
        )}

        {!principal && (
          <div className="bg-slate-100 dark:bg-slate-700 p-6 rounded-xl text-center">
            <p className="font-bold text-slate-800 dark:text-slate-100">No hay puntos disponibles</p>
          </div>
        )}

        {principal && (
          <button
            onClick={() => abrirMapa(principal)}
            className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2"
          >
            <Map size={20} /> Ir ahora
          </button>
        )}
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
              <p className="text-sm text-slate-600 dark:text-slate-300">🚶 {selected.distancia_min} min</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">{formatUpdatedAt(selected.updatedAt)}</p>
            </div>
            <button onClick={() => abrirMapa(selected)} className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 flex items-center justify-center gap-2"><Map size={20} /> Ir ahora</button>
            <button onClick={() => setSelected(null)} className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold flex items-center justify-center gap-2"><X size={16} /> Cerrar</button>
          </div>
        </>
      )}
    </div>
  )
}

export default ServiciosGenerales
