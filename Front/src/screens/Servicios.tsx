import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Bus, UtensilsCrossed, Bath, Droplets, Armchair, HeartPulse, ChevronRight } from 'lucide-react'

const Servicios = () => {
  const navigate = useNavigate()

  const menuItems = [
    {
      icon: Bus,
      label: 'Transporte',
      description: 'Encontrá dónde tomar transporte',
      route: '/servicios/transporte',
      colorScheme: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
    },
    {
      icon: UtensilsCrossed,
      label: 'Comer',
      description: 'Zonas gastronómicas cercanas',
      route: '/servicios/comer',
      colorScheme: 'bg-success/10 dark:bg-success/20 text-success'
    },
    {
      icon: Bath,
      label: 'Baños',
      description: 'Baños y puntos de hidratación',
      route: '/servicios/generales',
      colorScheme: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400'
    }
  ]

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Servicios" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-3">
        {menuItems.map((item) => {
          const Icon = item.icon
          return (
            <button
              key={item.route}
              onClick={() => navigate(item.route)}
              className="w-full bg-white dark:bg-slate-800 p-4 rounded-xl shadow-md hover:shadow-lg transition-all active:scale-[0.98] text-left"
            >
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-xl ${item.colorScheme} flex items-center justify-center shrink-0`}>
                  <Icon size={24} />
                </div>
                <div className="flex-1">
                  <p className="font-bold text-slate-800 dark:text-slate-100">
                    {item.label}
                  </p>
                  <p className="text-sm text-slate-500 dark:text-slate-300">
                    {item.description}
                  </p>
                </div>
                <ChevronRight size={18} className="text-slate-400" />
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default Servicios
