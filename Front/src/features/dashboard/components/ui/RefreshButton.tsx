import { RefreshCw } from 'lucide-react';
import { Button } from './Button';

interface RefreshButtonProps {
  onClick: () => void;
  loading?: boolean;
  size?: 'sm' | 'md';
}

export function RefreshButton({ onClick, loading = false, size = 'sm' }: RefreshButtonProps) {
  return (
    <Button
      variant="secondary"
      size={size}
      onClick={onClick}
      disabled={loading}
    >
      <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
      {loading ? 'Actualizando...' : 'Actualizar'}
    </Button>
  );
}