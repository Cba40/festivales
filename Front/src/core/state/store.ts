// src/core/state/store.ts

import { create } from 'zustand';
import type { Zone, Incident } from '@/features/dashboard/types';

// ============================================
// DATOS SEED — Mock inicial para desarrollo
// ============================================

const SEED_ZONES: Zone[] = [
  {
    id: 'zone-est-norte',
    name: 'Estacionamiento Norte',
    type: 'estacionamiento',
    saturation: 'alto',
    status: 'activa',
    capacity: 400,
    availableCapacity: 60,
  },
  {
    id: 'zone-est-sur',
    name: 'Estacionamiento Sur',
    type: 'estacionamiento',
    saturation: 'bajo',
    status: 'activa',
    capacity: 300,
    availableCapacity: 240,
  },
  {
    id: 'zone-trans-a',
    name: 'Parada Línea A',
    type: 'transporte',
    saturation: 'medio',
    status: 'activa',
    capacity: 150,
    availableCapacity: 75,
  },
  {
    id: 'zone-trans-b',
    name: 'Parada Express',
    type: 'transporte',
    saturation: 'bajo',
    status: 'activa',
    capacity: 100,
    availableCapacity: 85,
  },
  {
    id: 'zone-comida-central',
    name: 'Food Truck Central',
    type: 'comida',
    saturation: 'medio',
    status: 'activa',
    capacity: 200,
    availableCapacity: 90,
  },
  {
    id: 'zone-comida-parrilla',
    name: 'Zona Gastronómica',
    type: 'comida',
    saturation: 'alto',
    status: 'restringida',
    capacity: 180,
    availableCapacity: 27,
  },
  {
    id: 'zone-descanso',
    name: 'Plaza de Descanso',
    type: 'descanso',
    saturation: 'bajo',
    status: 'activa',
    capacity: 120,
    availableCapacity: 100,
  },
  {
    id: 'zone-emergencia',
    name: 'Primeros Auxilios',
    type: 'emergencia',
    saturation: 'bajo',
    status: 'activa',
    capacity: 50,
    availableCapacity: 45,
  },
  {
    id: 'zone-servicios',
    name: 'Baños Norte',
    type: 'servicios',
    saturation: 'alto',
    status: 'activa',
    capacity: 80,
    availableCapacity: 12,
  },
  {
    id: 'zone-est-gral',
    name: 'Estacionamiento General',
    type: 'estacionamiento',
    saturation: 'colapsado',
    status: 'cerrada',
    capacity: 500,
    availableCapacity: 0,
  },
];

const SEED_INCIDENTS: Incident[] = [
  {
    id: 'inc-001',
    type: 'congestion',
    severity: 'alta',
    description: 'Congestión vehicular severa en acceso norte. Vehículos detenidos en doble fila.',
    status: 'abierto',
    createdAt: new Date(Date.now() - 15 * 60000).toISOString(),
    zoneId: 'zone-est-norte',
  },
  {
    id: 'inc-002',
    type: 'closure',
    severity: 'media',
    description: 'Estacionamiento General cerrado por capacidad completa.',
    status: 'en_progreso',
    createdAt: new Date(Date.now() - 45 * 60000).toISOString(),
    zoneId: 'zone-est-gral',
  },
  {
    id: 'inc-003',
    type: 'emergency',
    severity: 'baja',
    description: 'Persona con deshidratación leve atendida en módulo médico.',
    status: 'resuelto',
    createdAt: new Date(Date.now() - 90 * 60000).toISOString(),
    zoneId: 'zone-emergencia',
  },
];

// ============================================
// STORE GLOBAL — Zustand
// ============================================

interface AppState {
  // Auth
  auth: { token: string | null; isAuthenticated: boolean };

  // Data
  zones: Zone[];
  incidents: Incident[];

  // Actions — Auth
  login: (token: string) => void;
  logout: () => void;

  // Actions — Zones
  setZones: (zones: Zone[]) => void;
  updateZone: (id: string, updates: Partial<Zone>) => void;

  // Actions — Incidents
  setIncidents: (incidents: Incident[]) => void;
  addIncident: (incident: Incident) => void;
  updateIncident: (id: string, updates: Partial<Incident>) => void;
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
    set({ auth: { token: null, isAuthenticated: false } });
  },

  // Seed data para desarrollo
  zones: SEED_ZONES,
  incidents: SEED_INCIDENTS,

  // Zone mutations
  setZones: (zones) => set({ zones }),

  updateZone: (id, updates) =>
    set((state) => ({
      zones: state.zones.map((z) =>
        z.id === id ? { ...z, ...updates } : z
      ),
    })),

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
