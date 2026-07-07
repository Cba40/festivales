import { useState } from 'react';
import { Header } from '@/components/Header';
import { QuickAction } from '@/components/ActionButton';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Car, LogOut, Bus, UtensilsCrossed, Hotel, Info, MessageCircle, MapPinOff } from 'lucide-react';
import { useAppStore } from '@/core/state/store';
import { LocationPromptModal } from '@/components/LocationPromptModal';
import { EventStatusBar } from '@/features/public/components/EventStatusBar';
import { ZoneList } from '@/features/public/components/ZoneList';

const Home = () => {
  const navigate = useNavigate();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const locationPermissionDenied = useAppStore(s => s.locationPermissionDenied);
  const requestLocation = useAppStore(s => s.requestLocation);

  const handleBannerClick = async () => {
    if (navigator.permissions && navigator.permissions.query) {
      try {
        const res = await navigator.permissions.query({ name: 'geolocation' as PermissionName });
        if (res.state === 'denied') {
          setIsModalOpen(true);
          return;
        }
      } catch (err) {
        console.warn('[Permissions API] Error en query:', err);
      }
    }

    const success = await requestLocation();
    if (!success) {
      setIsModalOpen(true);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Festival Jesús María" ubicacion="Zona Centro" />

      <EventStatusBar />

      {locationPermissionDenied && (
        <button
          onClick={handleBannerClick}
          className="w-full bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white px-4 py-3 flex items-center justify-between gap-3 shadow-md transition-all duration-300 hover:shadow-lg animate-pulse"
        >
          <div className="flex items-center gap-2.5">
            <MapPinOff size={20} className="text-white flex-shrink-0" />
            <div className="text-left">
              <span className="font-bold text-sm leading-tight block">Ubicación desactivada</span>
              <span className="text-xs opacity-90 leading-tight block">Actívala para ver estacionamientos y servicios cercanos.</span>
            </div>
          </div>
          <span className="text-xs font-extrabold uppercase tracking-wide bg-white/20 px-2.5 py-1 rounded-full border border-white/10 hover:bg-white/30 transition-colors flex-shrink-0">
            Activar
          </span>
        </button>
      )}

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

        <ZoneList />

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
            className="w-full flex items-center gap-3 bg-primary/10 dark:bg-blue-950/50 hover:bg-primary/15 dark:hover:bg-blue-900/40 text-primary dark:text-blue-400 py-3.5 px-4 rounded-xl transition-all duration-200 text-left border border-primary/5 dark:border-blue-900/30"
          >
            <MessageCircle size={20} className="text-primary dark:text-blue-400" />
            <div>
              <p className="text-sm font-bold text-primary dark:text-blue-400">Preguntá algo rápido</p>
              <p className="text-xs text-primary/80 dark:text-blue-400/80">La app te ayuda a decidir rápido</p>
            </div>
          </button>
        </div>

        <div className="mt-8 pt-4 border-t border-slate-200 text-center">
          <button type="button" onClick={() => navigate('/dashboard/login')} className="text-xs text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 font-medium underline transition-colors">
            Acceso Operador Municipal
          </button>
        </div>
      </div>
      <LocationPromptModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
};

export default Home;
