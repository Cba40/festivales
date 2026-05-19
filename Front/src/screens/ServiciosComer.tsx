import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { X, UtensilsCrossed, MapPin, Clock, Users } from 'lucide-react'
import { getCorredoresOrdenados, type CorredorGastronomico, getTipoLabel, getSentarseLabel } from '@/data/mockCorredoresGastronomicos'
import { formatUpdatedAt } from '@/utils/formatTime'

const ServiciosComer = () => {
  const navigate = useNavigate()
  const [selectedCorredor, setSelectedCorredor] = useState<CorredorGastronomico | null>(null)

  const corredores = getCorredoresOrdenados().slice(0, 3)  // Solo 3: baja, media, alta
  const getSaturacionColor = (saturacion: string) => {
    switch (saturacion) {
      case 'baja': return 'bg-success/20 text-success'
      case 'media': return 'bg-warning/20 text-warning'
      case 'alta': return 'bg-danger/20 text-danger'
      default: return 'bg-gray-500/20 text-gray-500'
    }
  }

  const getSaturacionEmoji = (saturacion: string) => {
    switch (saturacion) {
      case 'baja': return '🟢'
      case 'media': return '🟡'
      case 'alta': return '🔴'
      default: return '⚪'
    }
  }

  const getSaturacionLabel = (saturacion: string) => {
    switch (saturacion) {
      case 'baja': return 'Baja saturación'
      case 'media': return 'Media saturación'
      case 'alta': return 'Alta saturación'
      default: return saturacion
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Comer" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-4 overflow-y-auto">
        {/* Encabezado informativo */}
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-md">
          <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-3">
            Zonas gastronómicas disponibles
          </h2>
          <div className="flex gap-3 text-xs text-gray-600 dark:text-gray-400">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-success" /> Baja</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-warning" /> Media</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-danger" /> Alta</span>
          </div>
        </div>

        {/* Cards de corredores */}
        <div className="space-y-3">
          {corredores.map((corredor, index) => (
            <button
              key={corredor.id}
              onClick={() => setSelectedCorredor(corredor)}
              className="w-full text-left"
            >
              <div className={`p-4 rounded-xl border-l-4 transition-all hover:shadow-md ${
                index === 0 
                  ? 'bg-white dark:bg-slate-800 border-success shadow-md' 
                  : 'bg-slate-50 dark:bg-slate-800/50 border-slate-300 dark:border-slate-700'
              }`}>
                <div className="flex justify-between items-start gap-2">
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-gray-900 dark:text-gray-100 text-base">
                    {corredor.nombre}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 flex items-center gap-1">
                    <UtensilsCrossed size={14} /> {getTipoLabel(corredor.tipo)}
                  </p>
                </div>
                  <span className={`px-2 py-1 rounded text-xs font-bold whitespace-nowrap ${getSaturacionColor(corredor.saturacion)}`}>
                    {getSaturacionEmoji(corredor.saturacion)} {getSaturacionLabel(corredor.saturacion)}
                  </span>
                </div>

                <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 flex items-center gap-1">
                  <MapPin size={14} /> {corredor.referencia}
                </p>

                <div className="flex gap-3 mt-2 text-sm text-gray-600 dark:text-gray-400">
                  <span className="flex items-center gap-1"><Clock size={14} /> {corredor.distancia} min</span>
                  <span className="flex items-center gap-1"><Users size={14} /> {getSentarseLabel(corredor.posibilidadSentarse)}</span>
                </div>

                <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">
                  {formatUpdatedAt(corredor.updatedAt)}
                </p>
              </div>
            </button>
          ))}
        </div>

        {/* Botón exploración */}
        <button
          onClick={() => navigate('/servicios/comer/mas')}
          className="w-full bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 py-3 rounded-xl font-bold transition-transform active:scale-95 border-2 border-slate-300 dark:border-slate-600"
        >
          🗺️ Ver todas las zonas gastronómicas
        </button>
      </div>

      {/* Bottom Sheet */}
      {selectedCorredor && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => setSelectedCorredor(null)}
          />
          <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
            <div
              className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
              onClick={() => setSelectedCorredor(null)}
            />

            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3">
              {selectedCorredor.nombre}
            </h3>

            <div className="space-y-2 mb-4">
              <p className="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-2">
                <UtensilsCrossed size={16} /> <strong>{getTipoLabel(selectedCorredor.tipo)}</strong>
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-2">
                <MapPin size={16} /> {selectedCorredor.referencia}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-2">
                <Clock size={16} /> {selectedCorredor.distancia} min caminando
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-2">
                <Users size={16} /> {getSentarseLabel(selectedCorredor.posibilidadSentarse)}
              </p>
              <div className={`text-sm font-semibold p-2 rounded ${getSaturacionColor(selectedCorredor.saturacion)}`}>
                {getSaturacionLabel(selectedCorredor.saturacion)}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                {formatUpdatedAt(selectedCorredor.updatedAt)}
              </p>
            </div>

            <button
              onClick={() => setSelectedCorredor(null)}
              className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold transition-transform active:scale-95 flex items-center justify-center gap-2"
            >
              <X size={16} />
              Cerrar
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default ServiciosComer
