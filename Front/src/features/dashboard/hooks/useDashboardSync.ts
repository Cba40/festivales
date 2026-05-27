import { useState, useCallback } from 'react';
import { useAppStore } from '../../../core/state/store';

export function useDashboardSync() {
  const { zones, incidents } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await new Promise((resolve) => setTimeout(resolve, 800));
    } catch (err) {
      setError('Error al sincronizar dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  return { zones, incidents, loading, error, refresh };
}
