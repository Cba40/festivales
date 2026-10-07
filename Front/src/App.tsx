import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { useAppStore } from './core/state/store';
import { useLoadIdentity } from './core/auth/useAuth';
import { useDashboardSync } from './features/dashboard/hooks/useDashboardSync';
import { useTerritorialPrediction } from './hooks/useContextEngine';
import { loadEventDayContext } from './utils/contextoEvento';
import { recargarFases } from './config/eventoConfig';
import { getParkingRecommendations } from './services/parkingProduct';
import { getGastronomyRecommendations, GASTRONOMY_LIMIT } from './services/gastronomyProduct';
import { getBathroomRecommendations, BATHROOM_LIMIT } from './services/bathroomProduct';
import { getRestRecommendations, REST_LIMIT } from './services/restProduct';
import { getHydrationRecommendations, HYDRATION_LIMIT } from './services/hydrationProduct';
import { getAccommodationRecommendations } from './services/accommodationProduct';
import { getExitRecommendations } from './services/exitProduct';
import { getCities, getProtocols } from './services/emergencyProduct';
import {
  recordActivity,
  type ActivityServiceCategory,
} from './services/activity';
import ProtectedRoute from './shared/components/ProtectedRoute';
import { useActiveEvent } from './hooks/useActiveEvent';
import { requireActiveEventId } from './services/activeEvent';

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
const ForbiddenScreen = lazy(() => import('./features/auth/screens/ForbiddenScreen'));
const UserManagementScreen = lazy(() => import('./features/dashboard/screens/UserManagementScreen'));

function buildProductParams(): Record<string, unknown> {
  const { userLocation, zones, eventDayId } = useAppStore.getState();
  return {
    speed: 1.5,
    accessibility_required: false,
    current_zone_id: zones[0]?.id || undefined,
    user_id: '00000000-0000-0000-0000-000000000000',
    access_level: 'STANDARD',
    // El backend resuelve la jornada activa por reloj si no recibe esto. Sin
    // `event_day_id` el dashboard veria la configuracion global de
    // `service_configs` en vez de la de la jornada que estas mirando.
    ...(eventDayId ? { event_day_id: eventDayId } : {}),
    ...(userLocation ? { latitude: userLocation[0], longitude: userLocation[1] } : {}),
  };
}

function ScreenLoading() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center gap-3 text-slate-500">
      <span
        aria-hidden="true"
        className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-600"
      />
      <span>Cargando...</span>
    </div>
  );
}

// Solamente rutas públicas con categoría contractual válida. El resto
// (/servicios, /resolver-ahora, /asistente, '/') NO emiten screen_open.
//
// '/emergencia' está deliberadamente ausente: esa pantalla no es una consulta
// de servicio sino un catálogo de protocolos. Emitir screen_open ahí mezclaba
// "abrieron la pantalla" con "eligieron un protocolo" dentro de la misma
// categoría y diluía la demanda real. La única señal de emergencias ahora es el
// `filter_change` con `protocolo=<id>` de EmergencyModule.
//
// Ojo: las filas `screen_open` con request_mode='/emergencia' que YA están en
// la base siguen renderizándose con su etiqueta gracias a FILTER_LABELS, por
// eso no se quitó esa entrada del formateador.
const SCREEN_OPEN_ROUTE_CATEGORY: Record<string, ActivityServiceCategory> = {
  '/estacionar': 'parking',
  '/servicios/comer': 'gastronomy',
};

function AppLayout() {
  const location = useLocation();
  const isDashboard = location.pathname.startsWith('/dashboard');

  // Consulta /auth/me una vez por sesión. Tiene que correr antes de que cualquier
  // `ProtectedRoute` decida: sin esto, un reload con un token válido se vería
  // como "no autenticado" hasta que respondiera la API.
  useLoadIdentity();
  const { refresh } = useDashboardSync();
  const { refresh: refreshPredictions } = useTerritorialPrediction();
  const setUserLocation = useAppStore(s => s.setUserLocation);
  const setLocationPermissionDenied = useAppStore(s => s.setLocationPermissionDenied);
  const requestLocation = useAppStore(s => s.requestLocation);
  const [isOnline, setIsOnline] = useState(() => navigator.onLine);

  // Evento activo, resuelto desde la jornada que configuró el operador.
  //
  // Antes era `import.meta.env.VITE_EVENT_ID`, horneado en el bundle: cambiar de
  // evento exigía redeploy y un valor viejo en `.env` hacía pedir zonas de un evento
  // inexistente. `requireActiveEventId()` se llama dentro de cada `useCallback`, o
  // sea en el momento de prefetchear y no al montar, así que un `throw` por evento
  // ausente cae en el `.catch(() => {})` de cada prefetch en vez de romper el render.
  const {
    activeEventId,
    isLoading: isLoadingActiveEvent,
    isMissing: isActiveEventMissing,
    resolve: resolveActiveEvent,
  } = useActiveEvent();
  const [activeEventGateTimedOut, setActiveEventGateTimedOut] = useState(false);

  useEffect(() => {
    if (!isLoadingActiveEvent) {
      setActiveEventGateTimedOut(false);
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setActiveEventGateTimedOut(true);
    }, 5000);
    return () => window.clearTimeout(timeoutId);
  }, [isLoadingActiveEvent]);

  const preloadParking = useCallback(() => {
    getParkingRecommendations(requireActiveEventId(), { ...buildProductParams(), limit: 4 }, 'prefetch').catch(() => {});
  }, []);

  const preloadGastronomy = useCallback(() => {
    getGastronomyRecommendations(requireActiveEventId(), { ...buildProductParams(), limit: GASTRONOMY_LIMIT }, 'prefetch').catch(() => {});
  }, []);

  const preloadBathroom = useCallback(() => {
    getBathroomRecommendations(requireActiveEventId(), { ...buildProductParams(), limit: BATHROOM_LIMIT }, 'prefetch').catch(() => {});
  }, []);

  const preloadRest = useCallback(() => {
    getRestRecommendations(requireActiveEventId(), { ...buildProductParams(), limit: REST_LIMIT }, 'prefetch').catch(() => {});
  }, []);

  const preloadHydration = useCallback(() => {
    getHydrationRecommendations(requireActiveEventId(), { ...buildProductParams(), limit: HYDRATION_LIMIT }, 'prefetch').catch(() => {});
  }, []);

  const preloadAccommodation = useCallback(() => {
    const { userLocation } = useAppStore.getState();
    getAccommodationRecommendations(requireActiveEventId(), {
      limit: 100,
      ...(userLocation ? { latitude: userLocation[0], longitude: userLocation[1] } : {}),
    }, 'prefetch').catch(() => {});
  }, []);

  const preloadExit = useCallback(() => {
    const { userLocation } = useAppStore.getState();
    getExitRecommendations(requireActiveEventId(), {
      ...(userLocation ? { latitude: userLocation[0], longitude: userLocation[1] } : {}),
    }, 'prefetch').catch(() => {});
  }, []);

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

  // Todo el prefetch y el contexto de jornada cuelgan de `activeEventId`: antes de
  // que resuelva, no hay contra qué consultar y cada request saldría con el ID
  // equivocado. Al resolverse, este efecto corre solo porque `activeEventId` cambió.
  useEffect(() => {
    if (!activeEventId) return;
    refresh();
    refreshPredictions();
    loadEventDayContext(activeEventId).then(() => recargarFases());
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
  }, [refresh, refreshPredictions, preloadParking, preloadGastronomy, preloadBathroom, preloadRest, preloadHydration, preloadAccommodation, preloadExit, preloadEmergency, activeEventId]);

  // Sondeo periódico. El evento activo se re-resuelve acá para que una jornada que
  // el operador marque a mitad de una sesión abierta se tome sin recargar la página.
  useEffect(() => {
    const refreshForResolvedEvent = () => {
      if (!useAppStore.getState().activeEventId) return;
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

    const id = setInterval(() => {
      void resolveActiveEvent();
      refreshForResolvedEvent();
    }, 30000);
    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        void resolveActiveEvent();
        refreshForResolvedEvent();
      }
    };
    const onFocus = () => {
      void resolveActiveEvent();
      refreshForResolvedEvent();
    };
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('focus', onFocus);
    return () => {
      clearInterval(id);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('focus', onFocus);
    };
  }, [refresh, preloadParking, preloadGastronomy, preloadBathroom, preloadRest, preloadHydration, preloadAccommodation, preloadExit, preloadEmergency, activeEventId, resolveActiveEvent]);

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

  const isEventIndependentDashboardRoute =
    location.pathname === '/dashboard/login' ||
    location.pathname === '/dashboard/denegado';

  // Aviso de evento no configurado. `requireActiveEventId()` lanza en cada prefetch
  // cuando no hay jornada activa, y esos errores se tragan con `.catch(() => {})`
  // (son prefetch, no datos que el usuario pidió). Sin este banner el operador vería
  // pantallas vacías sin explicación; con él, la causa queda a la vista.
  const shouldShowActiveEventNotice =
    !activeEventId &&
    !isEventIndependentDashboardRoute &&
    (isActiveEventMissing || !isLoadingActiveEvent || activeEventGateTimedOut);
  const activeEventBanner = shouldShowActiveEventNotice ? (
      <div className="print:hidden bg-amber-500 text-black text-center text-sm p-1">
        {isActiveEventMissing
          ? 'No hay evento activo configurado. Marcá una jornada como activa desde el dashboard.'
          : 'No se pudo resolver el evento activo. Verificá la conexión o marcá una jornada como activa desde el dashboard.'}
      </div>
    ) : null;

  if (
    isLoadingActiveEvent &&
    !activeEventGateTimedOut &&
    !isEventIndependentDashboardRoute
  ) {
    return <ScreenLoading />;
  }

  if (isDashboard) {
    return (
      <>
        {!isOnline && (
          <div className="print:hidden bg-yellow-500 text-black text-center text-sm p-1">
            Modo sin conexión. Se mostrarán datos disponibles localmente.
          </div>
        )}
        {activeEventBanner}
        <Suspense fallback={<ScreenLoading />}>
        <Routes>
        <Route path="/dashboard/login" element={<LoginScreen />} />
        {/* Sesión válida sin permiso: pantalla propia, no el login. Mandarlo al
            login lo haría pensar que su sesión expiró. */}
        <Route path="/dashboard/denegado" element={<ForbiddenScreen />} />
        {/* Gestión de usuarios: exige `users:read`, que solo tiene quien puede
            administering identidades. Un operador de campo que escriba la URL a
            mano cae en /dashboard/denegado, no en el login. */}
        <Route path="/dashboard/users" element={
          <ProtectedRoute permission="users:read">
            <UserManagementScreen />
          </ProtectedRoute>
        } />
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
      {activeEventBanner}
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
