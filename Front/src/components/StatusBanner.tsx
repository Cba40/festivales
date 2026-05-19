import { AlertTriangle, AlertCircle, CheckCircle } from 'lucide-react';

interface StatusBannerProps {
  estado: 'disponible' | 'alerta' | 'critico';
  mensaje: string;
}

export const StatusBanner = ({ estado, mensaje }: StatusBannerProps) => {
  const config = {
    disponible: {
      bg: 'bg-success',
      icon: <CheckCircle size={20} />,
      text: 'text-white'
    },
    alerta: {
      bg: 'bg-amber-500 animate-pulse',
      icon: <AlertTriangle size={20} className="text-amber-950" />,
      text: 'text-amber-950'
    },
    critico: {
      bg: 'bg-danger',
      icon: <AlertCircle size={20} />,
      text: 'text-white'
    },
  };

  const { bg, icon, text } = config[estado];

  return (
    <div className={`${bg} ${text} px-4 py-3 flex items-center gap-2 shadow-md transition-all duration-300`}>
      {icon}
      <span className="font-semibold text-base leading-tight">{mensaje}</span>
    </div>
  );
};
