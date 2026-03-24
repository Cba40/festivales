import { Navigation, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Zona } from '../data/mockZones';

interface ZonaCardProps {
  zona: Zona;
  tipo: 'primaria' | 'fallback' | 'advertencia' | 'completa';
  distanciaTexto?: string;
  accionTexto?: string;
}

export const ZonaCard = ({ zona, tipo, distanciaTexto, accionTexto }: ZonaCardProps) => {
  const tipoConfig = {
    primaria: {
      bg: 'bg-[#22c55e]',
      border: 'border-[#22c55e]',
      icon: '🟢',
      textColor: 'text-white',
    },
    fallback: {
      bg: 'bg-[#f59e0b]',
      border: 'border-[#f59e0b]',
      icon: '🟡',
      textColor: 'text-white',
    },
    advertencia: {
      bg: 'bg-[#dc2626]',
      border: 'border-[#dc2626]',
      icon: '🔴',
      textColor: 'text-white',
    },
    completa: {
      bg: 'bg-gray-100',
      border: 'border-gray-300',
      icon: '⚪',
      textColor: 'text-gray-800',
    },
  };

  const config = tipoConfig[tipo];

  const tendenciaIcon = {
    subiendo: <TrendingUp size={16} />,
    bajando: <TrendingDown size={16} />,
    estable: <Minus size={16} />,
  };

  return (
    <div className={`${config.bg} ${config.textColor} rounded-xl p-4 shadow-lg`}>
      <div className="flex items-start gap-3">
        <span className="text-2xl">{config.icon}</span>
        <div className="flex-1">
          <h3 className="font-bold text-lg mb-1">
            {accionTexto || zona.nombre}
          </h3>

          {distanciaTexto && (
            <div className="flex items-center gap-2 mb-2">
              <Navigation size={16} />
              <span className="text-sm font-semibold">{distanciaTexto}</span>
            </div>
          )}

          <div className="flex items-center gap-4 text-sm opacity-90">
            <div className="flex items-center gap-1">
              {tendenciaIcon[zona.tendencia]}
              <span className="capitalize">{zona.tendencia}</span>
            </div>
            <span>{zona.capacidad_estimada} lugares estimados</span>
          </div>

          <div className="mt-2 text-xs opacity-75">{zona.timestamp}</div>
        </div>
      </div>
    </div>
  );
};
