import { create } from 'zustand';
import type { Zone, Incident } from '@/features/dashboard/types';

// ============================================
// STORE GLOBAL — Zustand
// ============================================

function getInitialTheme(): boolean {
  const stored = localStorage.getItem('theme');
  if (stored) return stored === 'dark';
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

export const useThemeStore = create<{
  isDark: boolean;
  toggle: () => void;
}>((set) => ({
  isDark: getInitialTheme(),
  toggle: () =>
    set((state) => {
      const next = !state.isDark;
      localStorage.setItem('theme', next ? 'dark' : 'light');
      document.documentElement.classList.toggle('dark', next);
      return { isDark: next };
    }),
}));

interface AppState {
  // Auth
  auth: { token: string | null; isAuthenticated: boolean };

  // Data
  zones: Zone[];
  incidents: Incident[];

  // User location (GPS)
  userLocation: [number, number] | null;

  // Actions — Auth
  login: (token: string) => void;
  logout: () => void;

  // Actions — Zones
  setZones: (zones: Zone[]) => void;
  updateZone: (id: string, updates: Partial<Zone>) => void;
  addZone: (zone: Zone) => void;
  removeZone: (id: string) => void;
  updateZoneConfig: (id: string, updates: Partial<Zone>) => void;

  // Actions — Incidents
  setIncidents: (incidents: Incident[]) => void;
  addIncident: (incident: Incident) => void;
  updateIncident: (id: string, updates: Partial<Incident>) => void;

  // Actions — Location
  setUserLocation: (loc: [number, number] | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Auth state
  auth: {
    token: localStorage.getItem('auth_token'),
    isAuthenticated: !!localStorage.getItem('auth_token'),
  },

  // Auth mutations
  login: (token) => {
    localStorage.setItem('auth_token', token);
    set({ auth: { token, isAuthenticated: true } });
  },
  logout: () => {
    localStorage.removeItem('auth_token');
    set({ auth: { token: null, isAuthenticated: false }, zones: [], incidents: [] });
  },

  // User location
  userLocation: null,

  // Inicializar con un baño random por defecto para pruebas de mapa offline
  zones: [
    {
      id: 'svc-b-random',
      name: 'Baño Random de Prueba',
      type: 'servicios',
      subtipo: 'banos',
      lat: -30.976,
      lng: -64.090,
      referencia: 'Al lado del escenario principal',
      distancia_min: 3,
      capacity: 10,
      availableCapacity: 10,
      saturation: 'bajo',
      status: 'activa'
    }
  ],
  incidents: [],

  // Zone mutations
  setZones: (zones) => set({ zones }),

  updateZone: (id, updates) =>
    set((state) => ({
      zones: state.zones.map((z) =>
        z.id === id ? { ...z, ...updates } : z
      ),
    })),

  addZone: (zone) =>
    set((state) => ({
      zones: [...state.zones, zone],
    })),

  removeZone: (id) =>
    set((state) => ({
      zones: state.zones.filter((z) => z.id !== id),
    })),

  updateZoneConfig: (id, updates) =>
    set((state) => ({
      zones: state.zones.map((z) =>
        z.id === id ? { ...z, ...updates } : z
      ),
    })),

  // Location mutations
  setUserLocation: (loc) => set({ userLocation: loc }),

  // Incident mutations
  setIncidents: (incidents) => set({ incidents }),

  addIncident: (incident) =>
    set((state) => ({
      incidents: [incident, ...state.incidents],
    })),

  updateIncident: (id, updates) =>
    set((state) => ({
      incidents: state.incidents.map((inc) =>
        inc.id === id ? { ...inc, ...updates } : inc
      ),
    })),
}));
