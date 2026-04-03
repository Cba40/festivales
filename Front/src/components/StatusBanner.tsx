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
    },
    alerta: {
      bg: 'bg-warning',
      icon: <AlertTriangle size={20} />,
    },
    critico: {
      bg: 'bg-danger',
      icon: <AlertCircle size={20} />,
    },
  };

  const { bg, icon } = config[estado];

  return (
    <div className={`${bg} text-white px-4 py-3 flex items-center gap-2 shadow-md`}>
      {icon}
      <span className="font-semibold text-base">{mensaje}</span>
    </div>
  );
};
