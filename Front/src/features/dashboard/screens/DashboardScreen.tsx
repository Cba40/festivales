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
import { usePermission, useRole } from '@/core/auth/useAuth';

const DEFAULT_EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

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
  hint?: string;
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    icon: Eye,
    title: 'Registrar Observación',
    description: 'Ingresar densidad o estado manual de una zona.',
    accent: 'text-indigo-600',
    iconBg: 'bg-indigo-50 border-indigo-100',
    path: '/dashboard/motor?tab=observations',
    hint: 'Ir a Motor › Observaciones',
  },
  {
    icon: AlertTriangle,
    title: 'Reportar Incidente',
    description: 'Crear alerta operativa o imprevisto.',
    accent: 'text-red-600',
    iconBg: 'bg-red-50 border-red-100',
    path: '/dashboard/operational-events',
  },
  {
    icon: BarChart3,
    title: 'Ver Predicciones en Vivo',
    description: 'Monitorear estado y saturación del territorio.',
    accent: 'text-emerald-600',
    iconBg: 'bg-emerald-50 border-emerald-100',
    path: '/dashboard/motor?tab=predictions',
    hint: 'Ir a Motor › Predicciones',
  },
  {
    icon: Lightbulb,
    title: 'Recomendaciones del Sistema',
    description: 'Revisar sugerencias de ajuste del motor.',
    accent: 'text-amber-600',
    iconBg: 'bg-amber-50 border-amber-100',
    path: '/dashboard/motor?tab=analytics',
    hint: 'Ir a Motor › Analytics',
  },
  {
    icon: Megaphone,
    title: 'Alertas y Mensajes',
    description: 'Comunicar alertas y mensajes al público.',
    accent: 'text-teal-600',
    iconBg: 'bg-teal-50 border-teal-100',
    path: '/dashboard/alerts',
  },
  {
    icon: BarChart3,
    title: 'Informes del Evento',
    description: 'Consultar informes municipales del evento (cobertura, zonas, incidencias).',
    accent: 'text-blue-600',
    iconBg: 'bg-blue-50 border-blue-100',
    path: '/dashboard/reports',
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
  const role = useRole();
  const puedeGestionarUsuarios = usePermission('users:read');
  const puedeVerConfig = usePermission('config:read');
  const puedeVerInformes = usePermission('reports:read');
  const puedeVerAnalisis = usePermission('analytics:read');
  const puedeVerMotor = puedeVerAnalisis || usePermission('events:read') || usePermission('observations:read');
  const puedeVerAlertas = usePermission('emergency:read');
  const puedeVerIncidentes = usePermission('emergency:write');
  const puedeVerPredicciones = usePermission('events:read');
  const logout = useAppStore((state) => state.logout);
  const [syncTime, setSyncTime] = useState(() => new Date());
  const [refreshing, setRefreshing] = useState(false);

  const { zones, refresh: refreshZones } = useDashboardSync();
  const { eventDays, refresh: refreshDays } = useEventDays(DEFAULT_EVENT_ID);
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
            {role === 'OPERADOR_CAMPO' && puedeVerMotor && (
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
            {puedeVerIncidentes && (
              <button
                onClick={() => navigate('/dashboard/operational-events')}
                className="flex items-center gap-2 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 py-2 px-3 rounded-lg transition-colors"
              >
                <AlertTriangle className="w-4 h-4" />
                Registrar Incidente
              </button>
            )}
            {puedeVerAlertas && (
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
            {role !== 'OPERADOR_CAMPO' && puedeVerMotor && (
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {QUICK_ACTIONS.map((action) => (
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