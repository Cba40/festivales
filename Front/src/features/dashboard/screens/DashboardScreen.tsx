import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Eye,
  AlertTriangle,
  BarChart3,
  Lightbulb,
  Activity,
  Wifi,
  Megaphone,
  FileText,
  Bell,
  Brain,
  CalendarDays,
  Map,
  LogOut,
  Users,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useAppStore } from '../../../core/state/store';
import { DashboardHeader } from '../components/DashboardHeader';
import { AppFooter } from '@/components/AppFooter';
import { useDashboardSync } from '../hooks/useDashboardSync';
import { useEventDays } from '../hooks/useEventDays';
import { useOperationalEvents } from '../hooks/useOperationalEvents';
import { RefreshButton } from '../components/ui';
import { useExactRole, usePermission } from '@/core/auth/useAuth';

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

interface QuickAction {
  icon: LucideIcon;
  title: string;
  description: string;
  accent: string;
  iconBg: string;
  path: string;
  /**
   * Permiso que habilita la tarjeta. Va acá y no como un `&&` suelto en el
   * render: asi la lista de acciones y su regla de acceso viven en el mismo lugar,
   * y agregar una tarjeta al array no puede olvidarse de declararla.
   */
  permission: string;
  hint?: string;
}

/**
 * Códigos de permiso de las acciones rápidas y de los botones del encabezado.
 *
 * Constantes y no strings sueltos porque los dos lados las necesitan: si la
 * tarjeta de "Alertas y Mensajes" usara un código y el botón del encabezado otro,
 * el menú prometería una pantalla que la tarjeta esconde. Con una sola fuente, esa
 * divergencia no se puede escribir.
 *
 * Deben coincidir 1:1 con `app/core/permissions.py` del backend. Ojo: `alerts:write`
 * e `incidents:write` son las acciones de campo (publicar una alerta, reportar un
 * incidente) y NO son `emergency:write`, que es configuración de infraestructura.
 */
const PERMISOS = {
  observacion: 'observations:write',
  incidente: 'incidents:write',
  alertas: 'alerts:write',
  predicciones: 'events:read',
  recomendaciones: 'analytics:read',
  informes: 'reports:read',
} as const;

const QUICK_ACTIONS: QuickAction[] = [
  {
    icon: Eye,
    title: 'Registrar Observación',
    description: 'Ingresar densidad o estado manual de una zona.',
    accent: 'text-indigo-600',
    iconBg: 'bg-indigo-50 border-indigo-100',
    path: '/dashboard/motor?tab=observations',
    permission: PERMISOS.observacion,
    hint: 'Ir a Motor › Observaciones',
  },
  {
    icon: AlertTriangle,
    title: 'Reportar Incidente',
    description: 'Crear alerta operativa o imprevisto.',
    accent: 'text-red-600',
    iconBg: 'bg-red-50 border-red-100',
    path: '/dashboard/operational-events',
    permission: PERMISOS.incidente,
  },
  {
    icon: BarChart3,
    title: 'Ver Predicciones en Vivo',
    description: 'Monitorear estado y saturación del territorio.',
    accent: 'text-emerald-600',
    iconBg: 'bg-emerald-50 border-emerald-100',
    path: '/dashboard/motor?tab=predictions',
    permission: PERMISOS.predicciones,
    hint: 'Ir a Motor › Predicciones',
  },
  {
    icon: Lightbulb,
    title: 'Recomendaciones del Sistema',
    description: 'Revisar sugerencias de ajuste del motor.',
    accent: 'text-amber-600',
    iconBg: 'bg-amber-50 border-amber-100',
    path: '/dashboard/motor?tab=analytics',
    permission: PERMISOS.recomendaciones,
    hint: 'Ir a Motor › Analytics',
  },
  {
    icon: Megaphone,
    title: 'Alertas y Mensajes',
    description: 'Comunicar alertas y mensajes al público.',
    accent: 'text-teal-600',
    iconBg: 'bg-teal-50 border-teal-100',
    path: '/dashboard/alerts',
    permission: PERMISOS.alertas,
  },
  {
    icon: BarChart3,
    title: 'Informes del Evento',
    description: 'Consultar informes municipales del evento (cobertura, zonas, incidencias).',
    accent: 'text-blue-600',
    iconBg: 'bg-blue-50 border-blue-100',
    path: '/dashboard/reports',
    permission: PERMISOS.informes,
  },
];

interface SystemMetric {
  icon: LucideIcon;
  label: string;
  value: string;
  sub: string;
  accent: string;
  iconBg: string;
}

export function DashboardScreen() {
  const navigate = useNavigate();
  // Botón de "Usuarios". `false` mientras se carga la identidad, así que no
  // parpadea ni aparece en un render con el usuario todavía desconocido.
  // `useExactRole`, no `useRole`: este flag RESTRINGE. Con `useRole` el super
  // admin respondía true para 'OPERADOR_CAMPO' sin serlo y se comía su propia
  // restricción, perdiendo el botón de "Motor y Análisis".
  const esOperadorCampo = useExactRole('OPERADOR_CAMPO');
  const puedeGestionarUsuarios = usePermission('users:read');
  const puedeVerConfig = usePermission('config:read');
  const puedeVerInformes = usePermission(PERMISOS.informes);
  const puedeVerAnalisis = usePermission(PERMISOS.recomendaciones);
  // Un `usePermission` por permiso, sin `||` entre ellos: encadenarlos con cortocircuito
  // hacía que algunos hooks no se ejecutaran según el usuario, y React exige el
  // mismo orden en cada render. Además el atajo devolvía el resultado del primer
  // permiso, no "tiene alguno de estos".
  const puedeVerEventos = usePermission(PERMISOS.predicciones);
  const puedeVerObservaciones = usePermission('observations:read');

  // Las tres acciones de campo. Son las únicas tarjetas que ve un OPERADOR_CAMPO:
  // registrar observación, reportar incidente y publicar alertas o mensajes.
  const puedeRegistrarObs = usePermission(PERMISOS.observacion);
  const puedeReportarIncidente = usePermission(PERMISOS.incidente);
  const puedeGestionarAlertas = usePermission(PERMISOS.alertas);

  const puedeVerMotor = puedeVerAnalisis || puedeVerEventos || puedeVerObservaciones;
  const logout = useAppStore((state) => state.logout);
  const [syncTime, setSyncTime] = useState(() => new Date());
  const [refreshing, setRefreshing] = useState(false);

  // Las tarjetas se filtran por permiso contra este mapa, no con un `&&` dentro
  // del `.map()`. La diferencia práctica: si `QUICK_ACTIONS` gana una tarjeta con un
  // código que no está acá, el `undefined` la esconde. Un permiso sin declarar se
  // oculta, que es el fallo seguro; al revés, un permiso nuevo declarado acá y no
  // en las tarjetas no abre nada.
  const permisosConcedidos: Record<string, boolean> = {
    [PERMISOS.observacion]: puedeRegistrarObs,
    [PERMISOS.incidente]: puedeReportarIncidente,
    [PERMISOS.alertas]: puedeGestionarAlertas,
    [PERMISOS.predicciones]: puedeVerEventos,
    [PERMISOS.recomendaciones]: puedeVerAnalisis,
    [PERMISOS.informes]: puedeVerInformes,
  };
  const accionesVisibles = QUICK_ACTIONS.filter((a) => permisosConcedidos[a.permission]);

  // Evento activo del store global (`useActiveEvent`), no `VITE_EVENT_ID`.
  const eventId = useAppStore((s) => s.activeEventId);
  const { zones, refresh: refreshZones } = useDashboardSync();
  const { eventDays, refresh: refreshDays } = useEventDays(eventId);
  const todayIso = toISODate(new Date());
  const todayDayId = useMemo(
    () => eventDays.find((d) => d.date === todayIso && d.is_active)?.id ?? null,
    [eventDays, todayIso]
  );
  const { events: incidentEvents, refresh: refreshIncidents } = useOperationalEvents(todayDayId);

  useEffect(() => {
    const id = setInterval(() => setSyncTime(new Date()), 30000);
    return () => clearInterval(id);
  }, []);

  const handleLogout = () => { logout(); navigate('/'); };

  const handleRefresh = async () => {
    if (refreshing) return;
    setRefreshing(true);
    await Promise.allSettled([refreshZones(true), refreshDays(), refreshIncidents()]);
    setSyncTime(new Date());
    setRefreshing(false);
  };

  const criticalZones = zones.filter(
    (z) => z.saturation === 'alto' || z.saturation === 'colapsado'
  ).length;
  const activeIncidentsToday = incidentEvents.filter(
    (e) => e.is_incident && e.is_active
  ).length;

  const systemMetrics: SystemMetric[] = [
    {
      icon: Activity,
      label: 'Zonas en Estado Crítico',
      value: String(criticalZones),
      sub: criticalZones > 0 ? 'Saturación alta o colapsada' : 'Sin zonas críticas',
      accent: 'text-orange-600',
      iconBg: 'bg-orange-50 border-orange-100',
    },
    {
      icon: AlertTriangle,
      label: 'Incidentes Activos Hoy',
      value: String(activeIncidentsToday),
      sub: activeIncidentsToday > 0 ? 'Incidentes reportados' : 'Sin incidentes reportados',
      accent: 'text-red-600',
      iconBg: 'bg-red-50 border-red-100',
    },
    {
      icon: Wifi,
      label: 'Última Sincronización',
      value: syncTime.toLocaleTimeString('es-AR'),
      sub: 'Conectado',
      accent: 'text-emerald-600',
      iconBg: 'bg-emerald-50 border-emerald-100',
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <DashboardHeader
        title="Centro de Comando"
        subtitle="Operación Territorial"
        actions={
          <nav className="flex flex-wrap gap-2">
            <RefreshButton onClick={() => void handleRefresh()} loading={refreshing} />
            {esOperadorCampo && puedeVerMotor && (
              <button
                onClick={() => navigate('/dashboard/motor?tab=observations')}
                className="flex items-center gap-2 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 py-2 px-3 rounded-lg transition-colors"
              >
                <Eye className="w-4 h-4" />
                Observaciones
              </button>
            )}
            {puedeVerConfig && (
              <button
                onClick={() => navigate('/dashboard/event-config')}
                className="flex items-center gap-2 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 py-2 px-3 rounded-lg transition-colors"
              >
                <CalendarDays className="w-4 h-4" />
                Jornadas y Fases
              </button>
            )}
            {puedeVerConfig && (
              <button
                onClick={() => navigate('/dashboard/infrastructure')}
                className="flex items-center gap-2 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 py-2 px-3 rounded-lg transition-colors"
              >
                <Map className="w-4 h-4" />
                Gestión de Zonas
              </button>
            )}
            {/* Los dos botones de acciones de campo usan las MISMAS banderas que las
                tarjetas de "Acciones Rápidas". Antes iban por otros permisos
                (`emergency:read` y `emergency:write`) y el menú llegaba a pantallas
                que la grilla de tarjetas no mostraba. */}
            {puedeReportarIncidente && (
              <button
                onClick={() => navigate('/dashboard/operational-events')}
                className="flex items-center gap-2 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 py-2 px-3 rounded-lg transition-colors"
              >
                <AlertTriangle className="w-4 h-4" />
                Registrar Incidente
              </button>
            )}
            {puedeGestionarAlertas && (
              <button
                onClick={() => navigate('/dashboard/alerts')}
                className="flex items-center gap-2 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 py-2 px-3 rounded-lg transition-colors"
              >
                <Bell className="w-4 h-4" />
                Alertas y Mensajes
              </button>
            )}
            {puedeVerInformes && (
              <button
                onClick={() => navigate('/dashboard/reports')}
                className="flex items-center gap-2 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 py-2 px-3 rounded-lg transition-colors"
              >
                <FileText className="w-4 h-4" />
                Informes
              </button>
            )}
            {/* Solo para quien puede administrar identidades. Ocultarlo NO es la
                garantía: la ruta tiene `ProtectedRoute permission="users:read"`
                y el backend exige `users:write` en cada escritura. Esto solo evita
                ofrecerle un botón a alguien que recibiría 403. */}
            {puedeGestionarUsuarios && (
              <button
                onClick={() => navigate('/dashboard/users')}
                className="flex items-center gap-2 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 py-2 px-3 rounded-lg transition-colors"
              >
                <Users className="w-4 h-4" />
                Usuarios
              </button>
            )}
            {/* El botón de "Motor y Análisis" abre el motor entero, que incluye
                predicciones y analytics. Por eso se esconde al operador aunque
                `puedeVerMotor` sea true: ese flag se cumple con `observations:read`,
                que le da acceso legitimo a la pantalla de observaciones, no a las de
                análisis. */}
            {!esOperadorCampo && puedeVerMotor && (
              <button
                onClick={() => navigate('/dashboard/motor')}
                className="flex items-center gap-2 text-sm bg-purple-600 hover:bg-purple-700 text-white py-2 px-3 rounded-lg transition-colors"
              >
                <Brain className="w-4 h-4" />
                Motor y Análisis
              </button>
            )}
            <button
              onClick={handleLogout}
              type="button"
              className="flex items-center gap-2 text-sm bg-red-600 hover:bg-red-700 text-white py-2 px-3 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Cerrar Sesión
            </button>
          </nav>
        }
      />

      <main className="p-4 sm:p-6 max-w-5xl mx-auto space-y-8">
        <section>
          <h2 className="text-lg font-semibold text-slate-700 mb-4">Acciones Rápidas</h2>
          {/* Una tarjeta por acción DECLARADA; lo que se filtra es cuáles se
              dibujan. Ninguna se borra del código: las seis siguen en
              `QUICK_ACTIONS` con su permiso, y las ve quien lo tenga. Para un
              OPERADOR_CAMPO quedan exactamente tres —Registrar Observación,
              Reportar Incidente y Alertas y Mensajes— porque es lo único que
              concede su rol. */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {accionesVisibles.map((action) => (
              <button
                key={action.title}
                onClick={() => navigate(action.path)}
                className="text-left bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md hover:border-indigo-300 hover:-translate-y-0.5 transition-all group"
              >
                <div className="flex items-start gap-4">
                  <span className={`flex items-center justify-center w-11 h-11 rounded-xl border ${action.iconBg}`}>
                    <action.icon className={`w-5 h-5 ${action.accent}`} />
                  </span>
                  <div>
                    <div className="font-semibold text-slate-800 group-hover:text-indigo-700">{action.title}</div>
                    <p className="text-xs text-slate-500 mt-1">{action.description}</p>
                    {action.hint && (
                      <p className="text-[10px] text-slate-400 mt-2">{action.hint}</p>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-slate-700 mb-4">Estado del Sistema</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {systemMetrics.map((metric) => (
              <div key={metric.label} className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <span className={`flex items-center justify-center w-10 h-10 rounded-xl border ${metric.iconBg}`}>
                    <metric.icon className={`w-5 h-5 ${metric.accent}`} />
                  </span>
                  <span className="text-2xl font-bold text-slate-800">{metric.value}</span>
                </div>
                <div className="text-sm font-semibold text-slate-700">{metric.label}</div>
                <p className="text-xs text-slate-400 mt-0.5">{metric.sub}</p>
              </div>
            ))}
          </div>
        </section>

        <AppFooter variant="private" />
      </main>
    </div>
  );
}