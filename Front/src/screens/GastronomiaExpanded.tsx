import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { MapPin } from 'lucide-react'
import { puntosComida } from '@/data/mockComer'
import { formatUpdatedAt } from '@/utils/formatTime'

interface Corredor {
  id: string
  nombre: string
  zona: string
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
  puntos: number
  referencia: string
  distancia_min: number
}

// Agrupar puntos en corredores simples
const corredores: Corredor[] = [
  {
    id: 'corredor-norte',
    nombre: 'Corredor Gastronómico Norte',
    zona: 'Frente a plaza secundaria',
    estado: 'bajo',
    puntos: 5,
    referencia: 'Puestos rápidos variados',
    distancia_min: 6
  },
  {
    id: 'corredor-central',
    nombre: 'Zona Gastronómica Central',
    zona: 'Predio principal',
    estado: 'alto',
    puntos: 12,
    referencia: 'Comidas y bebidas',
    distancia_min: 3
  },
  {
    id: 'corredor-oeste',
    nombre: 'Corredor Oeste',
    zona: 'Parque Autódromo',
    estado: 'medio',
    puntos: 7,
    referencia: 'Puestos variados',
    distancia_min: 8
  }
]

const getEstadoColor = (estado: string) => {
  switch (estado) {
    case 'bajo':
      return { bg: 'bg-success/20', border: 'border-success', text: 'text-success', label: '🟢 Baja' }
    case 'medio':
      return { bg: 'bg-warning/20', border: 'border-warning', text: 'text-warning', label: '🟡 Media' }
    case 'alto':
      return { bg: 'bg-danger/20', border: 'border-danger', text: 'text-danger', label: '🔴 Alta' }
    case 'colapsado':
      return { bg: 'bg-gray-500/20', border: 'border-gray-500', text: 'text-gray-500', label: '⚫ Colapsado' }
    default:
      return { bg: 'bg-slate-100', border: 'border-slate-300', text: 'text-slate-600', label: estado }
  }
}

const GastronomiaExpanded = () => {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Corredores Gastronómicos" showBack onBack={() => navigate('/servicios/comer')} />

      <div className="flex-1 p-4 space-y-3">
        {/* Leyenda simple */}
        <div className="bg-slate-100 dark:bg-slate-800 p-3 rounded-lg text-xs text-slate-600 dark:text-slate-300">
          <p className="font-bold mb-2">Saturación de demanda:</p>
          <div className="grid grid-cols-2 gap-2">
            <div>🟢 Baja: Menos espera</div>
            <div>🟡 Media: Espera moderada</div>
            <div>🔴 Alta: Espera extensa</div>
            <div>⚫ Colapsado: No ir ahora</div>
          </div>
        </div>

        {/* Corredores */}
        {corredores.map(corredor => {
          const colors = getEstadoColor(corredor.estado)
          return (
            <div
              key={corredor.id}
              className={`${colors.bg} border-2 ${colors.border} rounded-xl p-4 space-y-2`}
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className={`font-bold text-lg ${colors.text}`}>{corredor.nombre}</h3>
                  <div className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 mt-1">
                    <MapPin size={12} />
                    {corredor.zona}
                  </div>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-bold ${colors.text}`}>
                  {colors.label}
                </span>
              </div>

              <p className="text-sm text-slate-600 dark:text-slate-300">{corredor.referencia}</p>

              <div className="flex justify-between text-xs text-slate-500">
                <span>📍 {corredor.distancia_min} min</span>
                <span>🍽️ {corredor.puntos} puestos aprox.</span>
              </div>

              <button
                onClick={() => {
                  const punto = puntosComida.find(p => p.nombre.includes('Zona' === corredor.nombre.includes('Central')))
                  if (punto) {
                    window.open(
                      `https://www.google.com/maps/dir/?api=1&destination=${punto.lat},${punto.lng}`,
                      '_blank'
                    )
                  }
                }}
                className={`w-full py-2 rounded-lg font-bold text-sm transition-colors ${colors.text} bg-white dark:bg-slate-800 border border-current active:scale-95`}
              >
                Ver en mapa
              </button>
            </div>
          )
        })}

        <div className="text-xs text-slate-500 dark:text-slate-400 text-center pt-4">
          <p>💡 Actualizado hace momentos</p>
        </div>
      </div>
    </div>
  )
}

export default GastronomiaExpanded
