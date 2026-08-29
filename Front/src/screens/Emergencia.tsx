import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { EmergencyModule } from '@/components/EmergencyModule'

// ID de la ciudad del evento. Se define por entorno (VITE_CITY_ID) apuntando al
// UUID de la ciudad creada en el seed (p. ej. "Jesús María" en Neon). Si no se
// configura, el EmergencyModule muestra un aviso: el valor depende de la
// ciudad, no de un evento (módulo transversal).
const DEFAULT_CITY_ID = import.meta.env.VITE_CITY_ID || ''

const Emergencia = () => {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Emergencia" showBack onBack={() => navigate('/')} />
      <div className="flex-1 p-4 space-y-4 overflow-y-auto pb-20">
        <EmergencyModule cityId={DEFAULT_CITY_ID} />
      </div>
    </div>
  )
}

export default Emergencia
