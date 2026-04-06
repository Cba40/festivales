import { MapPin, ArrowLeft, Home } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';

interface HeaderProps {
  title: string;
  showBack?: boolean;
  onBack?: () => void;
  onHome?: () => void;
  ubicacion?: string;
}

export const Header = ({ title, showBack, onBack, onHome, ubicacion }: HeaderProps) => {
  const navigate = useNavigate();
  const location = useLocation();
  const isHome = location.pathname === '/';

  return (
    <header className="bg-primary text-white px-4 py-4 shadow-lg">
      <div className="flex items-center justify-between">
        {showBack ? (
          <button
            onClick={onBack}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            aria-label="Volver"
          >
            <ArrowLeft size={24} />
          </button>
        ) : (
          <div className="w-10" />
        )}

        <div className="flex-1 text-center">
          <h1 className="text-xl font-bold">{title}</h1>
          {ubicacion && (
            <div className="flex items-center justify-center gap-1 mt-1 text-sm opacity-90">
              <MapPin size={14} />
              <span>{ubicacion}</span>
            </div>
          )}
        </div>

        <div className="flex items-center">
          {!isHome && (
            <button
              onClick={() => {
                if (onHome) onHome();
                else navigate('/');
              }}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
              aria-label="Ir al Home"
            >
              <Home size={24} />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
