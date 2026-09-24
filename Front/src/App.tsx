import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { useAppStore } from './core/state/store';
import { useDashboardSync } from './features/dashboard/hooks/useDashboardSync';
import { useTerritorialPrediction } from './hooks/useContextEngine';
import { loadEventDayContext } from './utils/contextoEvento';
import { recargarFases } from './config/eventoConfig';
import { getParkingRecommendations } from './services/parkingProduct';
import { getGastronomyRecommendations } from './services/gastronomyProduct';
import { getBathroomRecommendations } from './services/bathroomProduct';
import { getRestRecommendations } from './services/restProduct';
import { getHydrationRecommendations } from './services/hydrationProduct';
import { getAccommodationRecommendations } from './services/accommodationProduct';
import { getExitRecommendations } from './services/exitProduct';
import { getCities, getProtocols } from './services/emergencyProduct';
import {
  recordActivity,
  type ActivityServiceCategory,
} from './services/activity';
import ProtectedRoute from './shared/components/ProtectedRoute';

const Home = lazy(() => import('./screens/Home'));
const Estacionar = lazy(() => import('./screens/Estacionar'));
const Emergencia = lazy(() => import('./screens/Emergencia'));
const Salir = lazy(() => import('./screens/Salir'));
const ResolverAhora = lazy(() => import('./screens/ResolverAhora'));
const Servicios = lazy(() => import('./screens/Servicios'));
const ServiciosTransporte = lazy(() => import('./screens/ServiciosTransporte'));
const ServiciosComer = lazy(() => import('./screens/ServiciosComer'));
const GastronomiaExpanded = lazy(() => import('./screens/GastronomiaExpanded'));
const ServiciosGenerales = lazy(() => import('./screens/ServiciosGenerales'));
const Pernoctar = lazy(() => import('./screens/Pernoctar'));
const AsistenteScreen = lazy(() => import('./screens/AsistenteScreen'));
const DashboardScreen = lazy(() =>
  import('./features/dashboard/screens/DashboardScreen').then((m) => ({ default: m.DashboardScreen }))
);
const InfrastructureScreen = lazy(() =>
  import('./features/dashboard/screens/InfrastructureScreen').then((m) => ({ default: m.InfrastructureScreen }))
);
const EventConfigScreen = lazy(() =>
  import('./features/dashboard/screens/EventConfigScreen').then((m) => ({ default: m.EventConfigScreen }))
);
const OperationalEventScreen = lazy(() =>
  import('./features/dashboard/screens/OperationalEventScreen').then((m) => ({ default: m.OperationalEventScreen }))
);
const AlertManagementScreen = lazy(() =>
  import('./features/dashboard/screens/AlertManagementScreen').then((m) => ({ default: m.AlertManagementScreen }))
);
const MotorScreen = lazy(() =>
  import('./features/dashboard/screens/MotorScreen').then((m) => ({ default: m.MotorScreen }))
);
const ReportsScreen = lazy(() =>
  import('@/features/dashboard/screens/ReportsScreen').then((m) => ({ default: m.ReportsScreen }))
);
const LoginScreen = lazy(() => import('./features/auth/screens/LoginScreen'));

function buildProductParams(): Record<string, unknown> {
  const { userLocation, zones } = useAppStore.getState();
  return {
    speed: 1.5,
    accessibility_required: false,
    current_zone_id: zones[0]?.id || undefined,
    user_id: '00000000-0000-0000-0000-000000000000',
    access_level: 'STANDARD',
    ...(userLocation ? { latitude: userLocation[0], longitude: userLocation[1] } : {}),
  };
}

function ScreenLoading() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center text-slate-500">
      <span>Cargando...</span>
    </div>
  );
}

// Solamente rutas públicas con categoría contractual válida. El resto
// (/servicios, /resolver-ahora, /asistente, '/') NO emiten screen_open.
const SCREEN_OPEN_ROUTE_CATEGORY: Record<string, ActivityServiceCategory> = {
  '/estacionar': 'parking',
  '/emergencia': 'emergency',
  '/salir': 'exit',
  '/servicios/transporte': 'transport',
  '/servicios/comer': 'gastronomy',
  '/servicios/comer/mas': 'gastronomy',
  '/pernoctar': 'accommodation',
};

function AppLayout() {
  const location = useLocation();
  const isDashboard = location.pathname.startsWith('/dashboard');
  const { refresh } = useDashboardSync();
  const { refresh: refreshPredictions } = useTerritorialPrediction();
  const setUserLocation = useAppStore(s => s.setUserLocation);
  const setLocationPermissionDenied = useAppStore(s => s.setLocationPermissionDenied);
  const requestLocation = useAppStore(s => s.requestLocation);
  const [isOnline, setIsOnline] = useState(() => navigator.onLine);

  const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

  const preloadParking = useCallback(() => {
    getParkingRecommendations(EVENT_ID, { ...buildProductParams(), limit: 4 }, 'prefetch').catch(() => {});
  }, [EVENT_ID]);

  const preloadGastronomy = useCallback(() => {
    getGastronomyRecommendations(EVENT_ID, { ...buildProductParams(), limit: 6 }, 'prefetch').catch(() => {});
  }, [EVENT_ID]);

  const preloadBathroom = useCallback(() => {
    getBathroomRecommendations(EVENT_ID, { ...buildProductParams(), limit: 10 }, 'prefetch').catch(() => {});
  }, [EVENT_ID]);

  const preloadRest = useCallback(() => {
    getRestRecommendations(EVENT_ID, { ...buildProductParams(), limit: 10 }, 'prefetch').catch(() => {});
  }, [EVENT_ID]);

  const preloadHydration = useCallback(() => {
    getHydrationRecommendations(EVENT_ID, { ...buildProductParams(), limit: 10 }, 'prefetch').catch(() => {});
  }, [EVENT_ID]);

  const preloadAccommodation = useCallback(() => {
    const { userLocation } = useAppStore.getState();
    getAccommodationRecommendations(EVENT_ID, {
      limit: 100,
      ...(userLocation ? { latitude: userLocation[0], longitude: userLocation[1] } : {}),
    }, 'prefetch').catch(() => {});
  }, [EVENT_ID]);

  const preloadExit = useCallback(() => {
    const { userLocation } = useAppStore.getState();
    getExitRecommendations(EVENT_ID, {
      ...(userLocation ? { latitude: userLocation[0], longitude: userLocation[1] } : {}),
    }, 'prefetch').catch(() => {});
  }, [EVENT_ID]);

  const preloadEmergency = useCallback(() => {
    getCities('prefetch').catch(() => {});
    getProtocols('festival', 'prefetch').catch(() => {});
  }, []);

  useEffect(() => {
    const onOnline = () => setIsOnline(true);
    const onOffline = () => setIsOnline(false);
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    return () => {
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
    };
  }, []);

  useEffect(() => {
    refresh();
    refreshPredictions();
    loadEventDayContext(EVENT_ID).then(() => recargarFases());
    preloadParking();
    preloadGastronomy();
    preloadBathroom();
    const t2 = setTimeout(() => {
      preloadRest();
      preloadHydration();
      preloadAccommodation();
      preloadExit();
      preloadEmergency();
    }, 500);
    return () => clearTimeout(t2);
  }, [refresh, refreshPredictions, preloadParking, preloadGastronomy, preloadBathroom, preloadRest, preloadHydration, preloadAccommodation, preloadExit, preloadEmergency, EVENT_ID]);

  useEffect(() => {
    const id = setInterval(() => {
      refresh();
      preloadParking();
      preloadGastronomy();
      preloadBathroom();
      preloadRest();
      preloadHydration();
      preloadAccommodation();
      preloadExit();
      preloadEmergency();
    }, 30000);
    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        refresh();
        preloadParking();
        preloadGastronomy();
        preloadBathroom();
        preloadRest();
        preloadHydration();
        preloadAccommodation();
        preloadExit();
        preloadEmergency();
      }
    };
    const onFocus = () => {
      refresh();
      preloadParking();
      preloadGastronomy();
      preloadBathroom();
      preloadRest();
      preloadHydration();
      preloadAccommodation();
      preloadExit();
      preloadEmergency();
    };
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('focus', onFocus);
    return () => {
      clearInterval(id);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('focus', onFocus);
    };
  }, [refresh, preloadParking, preloadGastronomy, preloadBathroom, preloadRest, preloadHydration, preloadAccommodation, preloadExit, preloadEmergency]);

  // 1. Escuchar el estado de los permisos de geolocalización de manera reactiva
  useEffect(() => {
    if (!navigator.permissions || !navigator.permissions.query) return;

    let permissionStatus: PermissionStatus | null = null;

    const handlePermissionChange = () => {
      if (!permissionStatus) return;
      if (permissionStatus.state === 'denied') {
        setLocationPermissionDenied(true);
      } else if (permissionStatus.state === 'granted') {
        setLocationPermissionDenied(false);
        requestLocation();
      } else {
        setLocationPermissionDenied(false);
      }
    };

    navigator.permissions.query({ name: 'geolocation' as PermissionName })
      .then((status) => {
        permissionStatus = status;
        if (status.state === 'denied') {
          setLocationPermissionDenied(true);
        } else {
          setLocationPermissionDenied(false);
        }
        status.addEventListener('change', handlePermissionChange);
      })
      .catch((err) => {
        console.warn('[Permissions API] Error:', err);
      });

    return () => {
      if (permissionStatus) {
        permissionStatus.removeEventListener('change', handlePermissionChange);
      }
    };
  }, [setLocationPermissionDenied, requestLocation]);

  // 2. Solicitar la ubicación inicial y mantener watchPosition
  useEffect(() => {
    requestLocation();

    if (!navigator.geolocation) return;

    const onSuccess = (pos: GeolocationPosition) => {
      setUserLocation([pos.coords.latitude, pos.coords.longitude]);
      setLocationPermissionDenied(false);
    };

    const onError = (err: GeolocationPositionError) => {
      if (err.code === err.PERMISSION_DENIED) {
        setLocationPermissionDenied(true);
      }
      console.warn('[GPS] Error:', err.message);
    };

    const id = navigator.geolocation.watchPosition(
      onSuccess,
      onError,
      { enableHighAccuracy: true, timeout: 30000, maximumAge: 60000 }
    );

    return () => navigator.geolocation.clearWatch(id);
  }, [setUserLocation, setLocationPermissionDenied, requestLocation]);

  // screen_open: evento de navegación REAL (interna, URL directa, back, forward).
  // Dedupe por pathname+tiempo para absorber renders y StrictMode sin duplicar.
  const lastScreenOpen = useRef<{ path: string; at: number } | null>(null);

  useEffect(() => {
    if (isDashboard) {
      lastScreenOpen.current = null;
      return;
    }
    const category = SCREEN_OPEN_ROUTE_CATEGORY[location.pathname];
    if (!category) return;
    const now = Date.now();
    const last = lastScreenOpen.current;
    if (last && last.path === location.pathname && now - last.at < 1000) return;
    lastScreenOpen.current = { path: location.pathname, at: now };
    recordActivity({
      interaction_type: 'screen_open',
      service_category: category,
      request_mode: location.pathname,
    });
  }, [location.pathname, isDashboard]);

  if (isDashboard) {
    return (
      <>
        {!isOnline && (
          <div className="print:hidden bg-yellow-500 text-black text-center text-sm p-1">
            Modo sin conexión. Se mostrarán datos disponibles localmente.
          </div>
        )}
        <Suspense fallback={<ScreenLoading />}>
        <Routes>
        <Route path="/dashboard/login" element={<LoginScreen />} />
        <Route path="/dashboard/*" element={
          <ProtectedRoute>
            <DashboardScreen />
          </ProtectedRoute>
        } />
        <Route path="/dashboard/infrastructure" element={
          <ProtectedRoute>
            <InfrastructureScreen />
          </ProtectedRoute>
        } />
        <Route path="/dashboard/event-config" element={
          <ProtectedRoute>
            <EventConfigScreen />
          </ProtectedRoute>
        } />
        <Route path="/dashboard/operational-events" element={<OperationalEventScreen />} />
        <Route path="/dashboard/alerts" element={<AlertManagementScreen />} />
        <Route path="/dashboard/motor" element={
          <ProtectedRoute>
            <MotorScreen />
          </ProtectedRoute>
        } />
        <Route path="/dashboard/reports" element={<ProtectedRoute><ReportsScreen /></ProtectedRoute>} />
        </Routes>
        </Suspense>
      </>
    );
  }

  return (
    <>
      {!isOnline && (
        <div className="bg-yellow-500 text-black text-center text-sm p-1">
          Modo sin conexión. Se mostrarán datos disponibles localmente.
        </div>
      )}
      <div className="min-h-screen bg-slate-50 flex justify-center">
        <div className="w-full max-w-md bg-white min-h-screen relative shadow-lg">
          <Suspense fallback={<ScreenLoading />}>
          <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/estacionar" element={<Estacionar />} />
          <Route path="/emergencia" element={<Emergencia />} />
          <Route path="/salir" element={<Salir />} />
          <Route path="/resolver-ahora" element={<ResolverAhora />} />
          <Route path="/servicios" element={<Servicios />} />
          <Route path="/servicios/transporte" element={<ServiciosTransporte />} />
          <Route path="/servicios/comer" element={<ServiciosComer />} />
          <Route path="/servicios/comer/mas" element={<GastronomiaExpanded />} />
          <Route path="/servicios/generales" element={<ServiciosGenerales />} />
          <Route path="/pernoctar" element={<Pernoctar />} />
          <Route path="/asistente" element={<AsistenteScreen />} />
          </Routes>
          </Suspense>
        </div>
      </div>
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}

export default App;
