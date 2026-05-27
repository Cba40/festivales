import { Header } from '@/components/Header';
import { StatusBanner } from '@/components/StatusBanner';
import { QuickAction } from '@/components/ActionButton';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Car, LogOut, Bus, UtensilsCrossed, Hotel, Info, MessageCircle } from 'lucide-react';

const Home = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Festival Jesús María" ubicacion="Zona Centro" />

      <StatusBanner estado="alerta" mensaje="Zona con alta demanda" />

      <div className="flex-1 p-4 space-y-6">
        <div>
          <h2 className="text-sm font-bold text-gray-600 dark:text-gray-300 mb-3 uppercase tracking-wide">
            Accesos rápidos
          </h2>
          <div className="grid grid-cols-2 min-[400px]:grid-cols-3 gap-3">
            <QuickAction
              icon={AlertTriangle}
              label="Emergencia"
              colorScheme="emergency"
              onClick={() => navigate('/emergencia')}
            />
            <QuickAction
              icon={Car}
              label="Estacionar"
              colorScheme="primary"
              onClick={() => navigate('/estacionar')}
            />
            <QuickAction
              icon={LogOut}
              label="Salir del evento"
              colorScheme="exit"
              onClick={() => navigate('/salir')}
            />
          </div>
        </div>

        <div>
          <h2 className="text-sm font-bold text-gray-600 dark:text-gray-300 mb-3 uppercase tracking-wide">
            Servicios
          </h2>
          <div className="grid grid-cols-2 min-[400px]:grid-cols-4 gap-3">
            <QuickAction
              icon={Bus}
              label="Transporte"
              colorScheme="transport"
              onClick={() => navigate('/servicios/transporte')}
            />
            <QuickAction
              icon={UtensilsCrossed}
              label="Comer"
              colorScheme="food"
              onClick={() => navigate('/servicios/comer')}
            />
            <QuickAction
              icon={Hotel}
              label="Hospedajes"
              colorScheme="lodging"
              onClick={() => navigate('/pernoctar')}
            />
            <QuickAction
              icon={Info}
              label="Más servicios"
              colorScheme="info"
              onClick={() => navigate('/servicios/generales')}
            />
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
          <button
            onClick={() => navigate('/asistente')}
            className="w-full flex items-center gap-3 bg-primary/10 dark:bg-primary/20 hover:bg-primary/15 dark:hover:bg-primary/25 text-primary py-3 px-4 rounded-xl transition-colors text-left"
          >
            <MessageCircle size={20} />
            <div>
              <p className="text-sm font-bold">Preguntá algo rápido</p>
              <p className="text-xs opacity-75">La app te ayuda a decidir rápido</p>
            </div>
          </button>
        </div>
      <div className="mt-8 pt-4 border-t border-slate-200 text-center">
        <button type="button" onClick={() => navigate('/dashboard/login')} className="text-xs text-slate-500 hover:text-blue-600 font-medium underline transition-colors">
          Acceso Operador Municipal
        </button>
      </div>
    </div>
  );
};

export default Home;
