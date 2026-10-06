import { create } from 'zustand';
import type { Zone } from '@/features/dashboard/types';

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

/**
 * Identidad del actor, la trae `GET /auth/me`.
 *
 * Antes el frontend no sabía quién era el usuario: `isAuthenticated` miraba que
 * hubiera *alguna cadena* en `localStorage`, así que un string no vacío ya
 * contaba como sesión válida. Ahora el token se valida contra el backend y de ahí
 * salen los permisos que decide qué se muestra.
 *
 * `permissions` llega filtrado: un operador de campo recibe 5, no los 19 del
 * administrador. Ocultar un menú no es una medida de seguridad —el backend igual
 * responde 403—, pero evita mostrar al operador pantallas que no puede usar.
 */
export interface AuthUser {
  id: string | null;
  username: string;
  /**
   * Nombre y apellido, si el usuario los cargo en su perfil. Informativo: la
   * identidad la define `username`. `null` cuando no lo completo, y por eso
   * siempre se muestra como `full_name || username`.
   */
  full_name: string | null;
  roles: string[];
  permissions: string[];
  is_provider_super_admin: boolean;
  is_superuser: boolean;
  scopes: { event_id: string | null; zone_id: string | null }[];
  is_global_scope: boolean;
}

interface AppState {
  // Auth
  auth: {
    token: string | null;
    isAuthenticated: boolean;
    user: AuthUser | null;
    /** true mientras se consulta /auth/me. Evita parpadeo de menús. */
    isLoadingUser: boolean;
  };

  /**
   * Evento contra el que se piden todos los datos.
   *
   * Antes venía de `import.meta.env.VITE_EVENT_ID`, que Vite hornea en el bundle
   * al compilar: cambiar de evento exigía redeploy, y un valor viejo en `.env`
   * hacía que la app pidiera zonas de un evento inexistente sin avisar
   * ("No se encontraron zonas para el evento").
   *
   * Ahora lo resuelve el backend desde la jornada activa que configuró el
   * operador (`GET /api/events/active`), así que marcar una jornada en el
   * dashboard basta para cambiar de evento.
   *
   * `null` hasta que resuelva y también cuando el backend responde 404 (no hay
   * jornada activa). No hay valor de respaldo hardcodeado a propósito: un ID
   * inventado produce 404 opaco en cada request, mientras que `null` deja
   * distinguir "todavía cargando" de "no hay evento configurado".
   */
  activeEventId: string | null;
  eventDayId: string | null;
  activeEventName: string | null;
  /** true mientras se consulta `/events/active`. Evita pedir datos sin event_id. */
  isLoadingActiveEvent: boolean;
  /** true si la resolución terminó y no hay jornada activa configurada. */
  activeEventMissing: boolean;

  // Data
  zones: Zone[];

  // User location (GPS)
  userLocation: [number, number] | null;
  locationPermissionDenied: boolean;

  // Actions — Auth
  login: (token: string) => void;
  logout: () => void;
  setUser: (user: AuthUser | null) => void;

  // Actions — Evento activo
  setActiveEvent: (
    eventId: string,
    eventDayId: string | null,
    eventName: string | null,
  ) => void;
  setActiveEventMissing: (missing: boolean) => void;

  // Actions — Zones
  setZones: (zones: Zone[]) => void;
  updateZone: (id: string, updates: Partial<Zone>) => void;
  addZone: (zone: Zone) => void;
  removeZone: (id: string) => void;
  updateZoneConfig: (id: string, updates: Partial<Zone>) => void;

  // Actions — Location
  setUserLocation: (loc: [number, number] | null) => void;
  setLocationPermissionDenied: (denied: boolean) => void;
  requestLocation: () => Promise<boolean>;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Auth state
  //
  // `isAuthenticated` ya NO se deduce de que haya un string en localStorage: se
  // pone en true recién cuando /auth/me confirma la identidad. Mientras tanto
  // `isLoadingUser` está en true y las rutas protegidas esperan, en vez de dejar
  // pasar a alguien con un token inválido y enterarse recién cuando la primera
  // API responde 401.
  auth: {
    token: localStorage.getItem('auth_token'),
    isAuthenticated: false,
    user: null,
    isLoadingUser: true,
  },

  // Auth mutations
  login: (token) => {
    localStorage.setItem('auth_token', token);
    set({ auth: { token, isAuthenticated: false, user: null, isLoadingUser: true } });
  },
  logout: () => {
    localStorage.removeItem('auth_token');
    set({
      auth: { token: null, isAuthenticated: false, user: null, isLoadingUser: false },
      zones: [],
    });
  },
  setUser: (user) =>
    set({
      auth: {
        token: get().auth.token,
        // Hay identidad confirmada: recién acá la sesión se considera activa.
        isAuthenticated: user !== null,
        user,
        isLoadingUser: false,
      },
    }),

  // Evento activo: lo inicializa `useActiveEvent()` al montar la app.
  activeEventId: null,
  eventDayId: null,
  activeEventName: null,
  isLoadingActiveEvent: true,
  activeEventMissing: false,

  setActiveEvent: (eventId, eventDayId, eventName) =>
    set({
      activeEventId: eventId,
      eventDayId,
      activeEventName: eventName,
      isLoadingActiveEvent: false,
      activeEventMissing: false,
    }),

  setActiveEventMissing: (missing) =>
    set({
      activeEventMissing: missing,
      isLoadingActiveEvent: false,
      // Sólo se limpia el ID si faltaba. Un 404 con un ID ya resuelto no debe
      // invalidar el evento en uso: el operador puede estar reconfigurando desde
      // el dashboard y vaciar el ID tiraría abajo todas las pantallas.
      ...(missing ? { activeEventId: null } : {}),
    }),

  // User location
  userLocation: (() => {
    const cached = localStorage.getItem('last_location');
    if (cached) { try { return JSON.parse(cached) as [number, number]; } catch { /* ignore */ } }
    return null;
  })(),
  locationPermissionDenied: false,

  // Las zonas se poblan exclusivamente desde useDashboardSync/API reales
  zones: [],
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
  setUserLocation: (coords) => {
    if (coords === null) {
      set({ userLocation: null })
      return
    }

    const prev = get().userLocation

    if (prev === null) {
      set({ userLocation: coords })
      localStorage.setItem('last_location', JSON.stringify(coords))
      return
    }

    const [lat1, lng1] = prev
    const [lat2, lng2] = coords

    const dLat = (lat2 - lat1) * 111320
    const dLng = (lng2 - lng1) * 111320 * Math.cos((lat1 * Math.PI) / 180)

    const distance = Math.sqrt(dLat * dLat + dLng * dLng)

    if (distance < 50) {
      return
    }

    set({ userLocation: coords })
    localStorage.setItem('last_location', JSON.stringify(coords))
  },

  setLocationPermissionDenied: (denied) => {
    set({ locationPermissionDenied: denied });
  },

  requestLocation: async () => {
    if (!navigator.geolocation) return false;
    return new Promise<boolean>((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const loc: [number, number] = [pos.coords.latitude, pos.coords.longitude];
          set({ locationPermissionDenied: false });
          get().setUserLocation(loc);
          resolve(true);
        },
        (err) => {
          if (err.code === err.PERMISSION_DENIED) {
            set({ locationPermissionDenied: true });
          }
          resolve(false);
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    });
  },
}));
