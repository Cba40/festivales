import { Header } from '@/components/Header';
import { StatusBanner } from '@/components/StatusBanner';
import { QuickAction } from '@/components/ActionButton';
import { useNavigate } from 'react-router-dom';

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
          <div className="grid grid-cols-3 gap-3">
            <QuickAction
              emoji="🚨"
              label="Emergencia"
              onClick={() => navigate('/emergencia')}
            />
            <QuickAction
              emoji="🚗"
              label="Estacionar"
              onClick={() => navigate('/estacionar')}
            />
            <QuickAction
              emoji="🚪"
              label="Salir"
              onClick={() => navigate('/salir')}
            />
          </div>
        </div>

        <div>
          <h2 className="text-sm font-bold text-gray-600 dark:text-gray-300 mb-3 uppercase tracking-wide">
            Servicios
          </h2>
          <div className="grid grid-cols-4 gap-3">
            <QuickAction
              emoji="🚌"
              label="Transporte"
              onClick={() => alert('Próximamente')}
            />
            <QuickAction
              emoji="🍽"
              label="Comer"
              onClick={() => alert('Puntos de comida cercanos')}
            />
            <QuickAction
              emoji="🛏"
              label="Descansar"
              onClick={() => alert('Zonas de descanso')}
            />
            <QuickAction
              emoji="🧭"
              label="Servicios"
              onClick={() => alert('Otros servicios')}
            />
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
          <button
            onClick={() => navigate('/resolver-ahora')}
            className="w-full bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl text-sm font-medium transition-colors"
          >
            ❓ No sabés qué hacer? → Resolver ahora
          </button>
        </div>
      </div>
    </div>
  );
};

export default Home;
