import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { MessageCircle, UtensilsCrossed, Car, Bath, Armchair, Trees } from 'lucide-react'

const chips = [
  { label: '¿Dónde comer?', icon: UtensilsCrossed },
  { label: '¿Dónde estacionar?', icon: Car },
  { label: '¿Dónde hay baños?', icon: Bath },
  { label: '¿Qué zona tiene menos gente?', icon: Trees },
  { label: '¿Dónde descansar?', icon: Armchair },
]

const AsistenteScreen = () => {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Asistente rápido" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-6">
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-md text-center">
          <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
            <MessageCircle size={28} className="text-primary" />
          </div>
          <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-2">
            Asistente rápido
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Próximamente podrás hacer preguntas rápidas sobre el evento
          </p>
        </div>

        <div>
          <p className="text-xs font-bold text-gray-600 dark:text-gray-300 mb-3 uppercase tracking-wide px-1">
            Preguntas frecuentes
          </p>
          <div className="space-y-2">
            {chips.map((chip) => {
              const Icon = chip.icon
              return (
                <div
                  key={chip.label}
                  className="w-full flex items-center gap-3 bg-white dark:bg-slate-800 px-4 py-3 rounded-xl shadow-md text-left opacity-60 cursor-not-allowed"
                >
                  <Icon size={18} className="text-slate-400 dark:text-slate-500" />
                  <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                    {chip.label}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

export default AsistenteScreen
