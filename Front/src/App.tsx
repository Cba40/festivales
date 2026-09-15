import { lazy, Suspense, useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { useAppStore } from './core/state/store';
import { useDashboardSync } from './features/dashboard/hooks/useDashboardSync';
import { useTerritorialPrediction } from './hooks/useContextEngine';
import { loadEventDayContext } from './utils/contextoEvento';
import { recargarFases } from './config/eventoConfig';
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
const MotorScreen = lazy(() =>
  import('./features/dashboard/screens/MotorScreen').then((m) => ({ default: m.MotorScreen }))
);
const LoginScreen = lazy(() => import('./features/auth/screens/LoginScreen'));

function ScreenLoading() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center text-slate-500">
      <span>Cargando...</span>
    </div>
  );
}

function AppLayout() {
  const location = useLocation();
  const isDashboard = location.pathname.startsWith('/dashboard');
  const { refresh } = useDashboardSync();
  const { refresh: refreshPredictions } = useTerritorialPrediction();
  const setUserLocation = useAppStore(s => s.setUserLocation);
  const setLocationPermissionDenied = useAppStore(s => s.setLocationPermissionDenied);
  const requestLocation = useAppStore(s => s.requestLocation);
  const [isOnline, setIsOnline] = useState(() => navigator.onLine);

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
    const eventId = import.meta.env.VITE_EVENT_ID || 'default-event-id';
    loadEventDayContext(eventId).then(() => recargarFases());
  }, [refresh, refreshPredictions]);

  useEffect(() => {
    const id = setInterval(refresh, 30000);
    const onVisibility = () => { if (document.visibilityState === 'visible') refresh(); };
    const onFocus = () => refresh();
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('focus', onFocus);
    return () => {
      clearInterval(id);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('focus', onFocus);
    };
  }, [refresh]);

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

  if (isDashboard) {
    return (
      <>
        {!isOnline && (
          <div className="bg-yellow-500 text-black text-center text-sm p-1">
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
        <Route path="/dashboard/motor" element={
          <ProtectedRoute>
            <MotorScreen />
          </ProtectedRoute>
        } />
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
