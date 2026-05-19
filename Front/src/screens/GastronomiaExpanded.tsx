import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { X } from 'lucide-react'
import { getCorredoresOrdenados, type CorredorGastronomico, getTipoLabel, getSentarseLabel } from '@/data/mockCorredoresGastronomicos'
import { formatUpdatedAt } from '@/utils/formatTime'

const GastronomiaExpanded = () => {
  const navigate = useNavigate()
  const [selectedCorredor, setSelectedCorredor] = useState<CorredorGastronomico | null>(null)
  const corredores = getCorredoresOrdenados()

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
      <Header title="Zonas Gastronómicas" showBack onBack={() => navigate('/servicios/comer')} />

      <div className="flex-1 p-4 space-y-4 overflow-y-auto">
        {/* Mapa visual */}
        <div className="w-full bg-white dark:bg-slate-800 rounded-xl border-2 border-slate-200 dark:border-slate-700 aspect-square relative overflow-hidden shadow-md">
          {/* Grid sutil de referencia */}
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

          {/* Puntos en el mapa */}
          {corredores.map(corredor => {
            const getMarkerColor = (sat: string) => {
              switch (sat) {
                case 'baja': return 'bg-success shadow-success/50'
                case 'media': return 'bg-warning shadow-warning/50'
                case 'alta': return 'bg-danger shadow-danger/50'
                default: return 'bg-gray-500 shadow-gray-500/50'
              }
            }

            const getEmoji = (sat: string) => {
              switch (sat) {
                case 'baja': return '🟢'
                case 'media': return '🟡'
                case 'alta': return '🔴'
                default: return '⚪'
              }
            }

            return (
              <button
                key={corredor.id}
                onClick={() => setSelectedCorredor(corredor)}
                className="absolute transform -translate-x-1/2 -translate-y-1/2 group z-10"
                style={{ left: `${corredor.x}%`, top: `${corredor.y}%` }}
                title={corredor.nombre}
              >
                {/* Aura */}
                <div className={`absolute -inset-2 rounded-full ${getMarkerColor(corredor.saturacion)} opacity-30 group-hover:opacity-50 transition-opacity blur-md`} />
                {/* Punto */}
                <div className={`relative w-8 h-8 rounded-full ${getMarkerColor(corredor.saturacion)} shadow-lg group-hover:scale-110 transition-transform flex items-center justify-center text-white font-bold text-sm border-2 border-white dark:border-slate-800`}>
                  {getEmoji(corredor.saturacion)}
                </div>
              </button>
            )
          })}
        </div>

        {/* Leyenda */}
        <div className="bg-white dark:bg-slate-800 rounded-xl p-3 shadow-md">
          <p className="text-xs font-bold text-slate-600 dark:text-slate-400 mb-2">📍 Leyenda:</p>
          <div className="space-y-1 text-xs text-slate-600 dark:text-slate-400">
            <p>🟢 Baja saturación - Fácil encontrar lugar</p>
            <p>🟡 Media saturación - Moderadamente disponible</p>
            <p>🔴 Alta saturación - Muy concurrido</p>
          </div>
        </div>

        {/* Lista de corredores */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-slate-600 dark:text-slate-400 px-1">
            {corredores.length} zonas disponibles
          </p>
          {corredores.map(corredor => (
            <button
              key={corredor.id}
              onClick={() => setSelectedCorredor(corredor)}
              className="w-full text-left bg-slate-50 dark:bg-slate-800/50 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-primary dark:hover:border-primary/50 transition-colors group"
            >
              <div className="flex items-start gap-2">
                <span className="text-lg mt-0.5">{getSaturacionEmoji(corredor.saturacion)}</span>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-primary dark:group-hover:text-primary">
                    {corredor.nombre}
                  </p>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                    🍽️ {getTipoLabel(corredor.tipo)}
                  </p>
                  <p className="text-xs text-slate-600 dark:text-slate-400">
                    🚶 {corredor.distancia} min
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
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
              <p className="text-sm text-slate-600 dark:text-slate-300">
                🍽️ <strong>{getTipoLabel(selectedCorredor.tipo)}</strong>
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                📍 {selectedCorredor.referencia}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                🚶 {selectedCorredor.distancia} min caminando
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                {getSentarseLabel(selectedCorredor.posibilidadSentarse)}
              </p>
              <div className={`text-sm font-semibold p-2 rounded ${getSaturacionColor(selectedCorredor.saturacion)}`}>
                {getSaturacionEmoji(selectedCorredor.saturacion)} {getSaturacionLabel(selectedCorredor.saturacion)}
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

export default GastronomiaExpanded
