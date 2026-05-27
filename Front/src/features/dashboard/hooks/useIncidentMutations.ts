import { useState } from 'react';
import { useAppStore } from '../../../core/state/store';
import { Incident } from '../types';

export function useIncidentMutations() {
  const addIncident = useAppStore((state) => state.addIncident);
  const [loading, setLoading] = useState(false);

  const reportIncident = async (data: Omit<Incident, 'id' | 'createdAt'>) => {
    setLoading(true);
    const newIncident: Incident = {
      ...data,
      id: `inc-${Date.now()}`,
      createdAt: new Date().toISOString(),
    };

    addIncident(newIncident);

    try {
      await new Promise((resolve) => setTimeout(resolve, 800));
    } catch (error) {
      console.error('Failed to report incident');
    } finally {
      setLoading(false);
    }
  };

  return { reportIncident, loading };
}
