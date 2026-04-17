import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Phone, Map } from 'lucide-react'
import { getPernoctesOrdenados } from '@/utils/pernoctar'
import { formatUpdatedAt } from '@/utils/formatTime'

const Pernoctar = () => {
  const navigate = useNavigate()
  const puntos = getPernoctesOrdenados()

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

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Pernoctar" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-3">
        {puntos.map(p => (
          <div key={p.id} className="bg-white dark:bg-slate-800 p-4 rounded-xl shadow-md space-y-2">
            <div className="flex justify-between items-start">
              <div>
                <p className="font-bold text-slate-800 dark:text-slate-100">{p.nombre}</p>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  <div className="text-sm font-semibold">
                    {p.categoria.toUpperCase()}
                  </div>
                  · {p.referencia}
                </p>
              </div>
              <span className={`px-2 py-1 rounded text-xs font-bold ${getDispBadge(p.disponibilidad)}`}>
                <div className="text-sm">
                  {p.disponibilidad === 'disponible' && '🟢 Disponible'}
                  {p.disponibilidad === 'consultar' && '🟡 Consultar'}
                  {p.disponibilidad === 'completo' && '🔴 Completo'}
                </div>
              </span>
            </div>

            <p className="text-sm text-slate-600 dark:text-slate-300">
              🚶 {p.distancia_min} min
            </p>
            <p className="text-xs text-slate-400 dark:text-slate-500">
              {formatUpdatedAt(p.updatedAt)}
            </p>
            <p className="text-xs text-gray-500">
              ℹ️ Confirmar disponibilidad por teléfono antes de ir
            </p>

            <div className="flex gap-2 pt-2">
              {p.telefono && (
                <a
                  href={`tel:${p.telefono}`}
                  className="flex-1 flex items-center justify-center gap-1 bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg font-bold text-sm transition-colors"
                >
                  <Phone size={16} /> Llamar
                </a>
              )}

              <button
                onClick={() => handleMaps(p.lat, p.lng)}
                className="flex-1 flex items-center justify-center gap-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg font-bold text-sm transition-colors"
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
      </div>
    </div>
  )
}

export default Pernoctar
