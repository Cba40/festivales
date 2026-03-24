import { Header } from '../components/Header';
import { StatusBanner } from '../components/StatusBanner';
import { ActionButton, QuickAction } from '../components/ActionButton';
import { ChevronRight } from 'lucide-react';

interface HomeProps {
  onNavigate: (screen: string) => void;
}

export const Home = ({ onNavigate }: HomeProps) => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header title="Festival Jesús María" ubicacion="Zona Centro" />

      <StatusBanner estado="alerta" mensaje="Zona con alta demanda" />

      <div className="flex-1 p-4 space-y-6">
        <div className="pt-4">
          <ActionButton
            icon={<ChevronRight size={28} />}
            label="Resolver ahora"
            onClick={() => onNavigate('estacionar')}
          />
        </div>

        <div>
          <h2 className="text-sm font-bold text-gray-600 mb-3 uppercase tracking-wide">
            Accesos rápidos
          </h2>
          <div className="grid grid-cols-3 gap-3">
            <QuickAction
              emoji="🚨"
              label="Emergencia"
              onClick={() => alert('Emergencias: 911')}
            />
            <QuickAction
              emoji="🚗"
              label="Estacionar"
              onClick={() => onNavigate('estacionar')}
            />
            <QuickAction
              emoji="🚪"
              label="Salir"
              onClick={() => alert('Mostrando salidas más cercanas...')}
            />
          </div>
        </div>

        <div>
          <h2 className="text-sm font-bold text-gray-600 mb-3 uppercase tracking-wide">
            Servicios
          </h2>
          <div className="grid grid-cols-4 gap-3">
            <QuickAction
              emoji="🚌"
              label="Movilidad"
              onClick={() => alert('Transporte disponible')}
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
      </div>
    </div>
  );
};
