import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Phone, Map, ChevronDown, Info, Clock } from 'lucide-react'
import { getPernoctesOrdenados } from '@/utils/pernoctar'
import { formatUpdatedAt } from '@/utils/formatTime'

const Pernoctar = () => {
  const navigate = useNavigate()
  const puntos = getPernoctesOrdenados()
  const [mostrarTodos, setMostrarTodos] = useState(false)

  const handleMaps = (lat: number, lng: number) => {
    const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
    window.open(url, '_blank')
  }

  const getDispBadge = (disp?: string) => {
    switch (disp) {
      case 'disponible': return 'bg-success/20 text-success'
      case 'completo': return 'bg-danger/20 text-danger'
      default: return 'bg-warning/20 text-warning'
    }
  }

  const getDispText = (disp?: string) => {
    switch (disp) {
      case 'disponible': return '🟢 Probable disponibilidad'
      case 'completo': return '🔴 Últimos lugares'
      default: return '🟡 Consultar disponibilidad'
    }
  }

  const mostrados = mostrarTodos ? puntos : puntos.slice(0, 3)

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Hospedajes" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-3 overflow-y-auto">
        {/* Microcopy informativo */}
        <p className="text-xs text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/50 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 flex items-center gap-2">
          <Info size={14} /> Los alojamientos pueden variar su disponibilidad durante el evento
        </p>

        {mostrados.map(p => (
          <div key={p.id} className="bg-white dark:bg-slate-800 p-4 rounded-xl shadow-md space-y-2">
            <div className="flex justify-between items-start">
              <div>
                <p className="font-bold text-slate-800 dark:text-slate-100">{p.nombre}</p>
                <div className="text-sm font-semibold text-slate-500 dark:text-slate-400">
                  {p.categoria.toUpperCase()}
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  · {p.referencia}
                </p>
              </div>
              <span className={`px-2 py-1 rounded text-xs font-bold ${getDispBadge(p.disponibilidad)}`}>
                {getDispText(p.disponibilidad)}
              </span>
            </div>

            <p className="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-1">
              <Clock size={14} /> {p.distancia_min} min
            </p>
            <p className="text-xs text-slate-400 dark:text-slate-500">
              {formatUpdatedAt(p.updatedAt)}
            </p>
            <p className="text-xs text-gray-500 flex items-center gap-1">
              <Info size={12} /> Confirmar disponibilidad por teléfono antes de ir
            </p>

            <div className="flex gap-2 pt-2">
              {p.telefono && (
                <a
                  href={`tel:${p.telefono}`}
                  className="flex-1 flex items-center justify-center gap-1 bg-success/10 hover:bg-success/20 text-success py-2 rounded-xl font-bold text-sm transition-colors"
                >
                  <Phone size={16} /> Llamar
                </a>
              )}

              <button
                onClick={() => handleMaps(p.lat, p.lng)}
                className="flex-1 flex items-center justify-center gap-1 bg-primary/10 hover:bg-primary/20 text-primary py-2 rounded-xl font-bold text-sm transition-colors"
              >
                <Map size={16} /> Ir ahora
              </button>
            </div>
          </div>
        ))}

        {puntos.length === 0 && (
          <div className="text-center text-slate-500 dark:text-slate-400 py-8">
            No hay alojamientos registrados
          </div>
        )}

        {/* Botón Ver más */}
        {!mostrarTodos && puntos.length > 3 && (
          <button
            onClick={() => setMostrarTodos(true)}
            className="w-full bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 py-3 rounded-xl font-bold transition-transform active:scale-95 border-2 border-slate-300 dark:border-slate-600 flex items-center justify-center gap-2"
          >
            <ChevronDown size={18} />
            Ver {puntos.length - 3} alojamientos más
          </button>
        )}

        {mostrarTodos && puntos.length > 3 && (
          <button
            onClick={() => setMostrarTodos(false)}
            className="w-full bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 py-3 rounded-xl font-bold transition-transform active:scale-95 border-2 border-slate-300 dark:border-slate-600"
          >
            Mostrar menos
          </button>
        )}
      </div>
    </div>
  )
}

export default Pernoctar
