import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'

const Servicios = () => {
  const navigate = useNavigate()

  const menuItems = [
    {
      emoji: '🚌',
      label: 'Transporte',
      description: 'Encontrá dónde tomar transporte',
      route: '/servicios/transporte'
    },
    {
      emoji: '🍽',
      label: 'Comer',
      description: 'Puntos de comida cercanos',
      route: '/servicios/comer'
    },
    {
      emoji: '🧭',
      label: 'Servicios Generales',
      description: 'Baños, agua, descanso y salud',
      route: '/servicios/generales'
    }
  ]

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Servicios" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-3">
        {menuItems.map((item) => (
          <button
            key={item.route}
            onClick={() => navigate(item.route)}
            className="w-full bg-white dark:bg-slate-800 p-4 rounded-xl text-left shadow-md hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
          >
            <div className="flex items-center gap-3">
              <span className="text-3xl">{item.emoji}</span>
              <div>
                <p className="font-bold text-slate-800 dark:text-slate-100">
                  {item.label}
                </p>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {item.description}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

export default Servicios
