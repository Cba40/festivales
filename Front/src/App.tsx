import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { useAppStore } from './core/state/store';
import Home from './screens/Home';
import Estacionar from './screens/Estacionar';
import Emergencia from './screens/Emergencia';
import Salir from './screens/Salir';
import ResolverAhora from './screens/ResolverAhora';
import Servicios from './screens/Servicios';
import ServiciosTransporte from './screens/ServiciosTransporte';
import ServiciosComer from './screens/ServiciosComer';
import GastronomiaExpanded from './screens/GastronomiaExpanded';
import ServiciosGenerales from './screens/ServiciosGenerales';
import Pernoctar from './screens/Pernoctar';
import AsistenteScreen from './screens/AsistenteScreen';
import { DashboardScreen } from './features/dashboard/screens/DashboardScreen';
import { useDashboardSync } from './features/dashboard/hooks/useDashboardSync';
import { loadEventDayContext } from './utils/contextoEvento';
import { recargarFases } from './config/eventoConfig';
import { ZoneUpdateScreen } from './features/dashboard/screens/ZoneUpdateScreen';
import { IncidentReportScreen } from './features/dashboard/screens/IncidentReportScreen';
import { ZoneAdminScreen } from './features/dashboard/screens/ZoneAdminScreen';
import { EventDayScreen } from './features/dashboard/screens/EventDayScreen';
import { OperationalProfileScreen } from './features/dashboard/screens/OperationalProfileScreen';
import { OperationalPhaseScreen } from './features/dashboard/screens/OperationalPhaseScreen';
import { ZoneBehaviorScreen } from './features/dashboard/screens/ZoneBehaviorScreen';
import { AttendanceLevelScreen } from './features/dashboard/screens/AttendanceLevelScreen';
import { OperationalEventScreen } from './features/dashboard/screens/OperationalEventScreen';
import { MotorConfigScreen } from './features/dashboard/screens/MotorConfigScreen';
import { EventConfigPage } from './pages/EventConfigPage';
import LoginScreen from './features/auth/screens/LoginScreen';
import ProtectedRoute from './shared/components/ProtectedRoute';

function AppLayout() {
  const location = useLocation();
  const isDashboard = location.pathname.startsWith('/dashboard');
  const { refresh } = useDashboardSync();
  const setUserLocation = useAppStore(s => s.setUserLocation);
  const setLocationPermissionDenied = useAppStore(s => s.setLocationPermissionDenied);
  const requestLocation = useAppStore(s => s.requestLocation);

  useEffect(() => {
    refresh();
    const eventId = import.meta.env.VITE_EVENT_ID || 'default-event-id';
    loadEventDayContext(eventId).then(() => recargarFases());
  }, [refresh]);

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
      { enableHighAccuracy: false, timeout: 30000, maximumAge: 15000 }
    );

    return () => navigator.geolocation.clearWatch(id);
  }, [setUserLocation, setLocationPermissionDenied, requestLocation]);

  if (isDashboard) {
    return (
      <Routes>
        <Route path="/dashboard/login" element={<LoginScreen />} />
        <Route path="/dashboard/*" element={
          <ProtectedRoute>
            <DashboardScreen />
          </ProtectedRoute>
        } />
        <Route path="/dashboard/zones" element={<ZoneUpdateScreen />} />
        <Route path="/dashboard/report" element={<IncidentReportScreen />} />
        <Route path="/dashboard/admin-zones" element={<ZoneAdminScreen />} />
        <Route path="/dashboard/event-days" element={<EventDayScreen />} />
        <Route path="/dashboard/profiles" element={<OperationalProfileScreen />} />
        <Route path="/dashboard/phases" element={<OperationalPhaseScreen />} />
        <Route path="/dashboard/zone-behaviors" element={<ZoneBehaviorScreen />} />
        <Route path="/dashboard/attendance" element={<AttendanceLevelScreen />} />
        <Route path="/dashboard/operational-events" element={<OperationalEventScreen />} />
        <Route path="/dashboard/motor-config" element={<MotorConfigScreen />} />
        <Route path="/dashboard/context-engine" element={
          <ProtectedRoute>
            <EventConfigPage />
          </ProtectedRoute>
        } />
      </Routes>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex justify-center">
      <div className="w-full max-w-md bg-white min-h-screen relative shadow-lg">
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
      </div>
    </div>
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
