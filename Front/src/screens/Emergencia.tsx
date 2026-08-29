import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { EmergencyModule } from '@/components/EmergencyModule'

const Emergencia = () => {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Emergencia" showBack onBack={() => navigate('/')} />
      <div className="flex-1 p-4 space-y-4 overflow-y-auto pb-20">
        <EmergencyModule context="festival" />
      </div>
    </div>
  )
}

export default Emergencia
