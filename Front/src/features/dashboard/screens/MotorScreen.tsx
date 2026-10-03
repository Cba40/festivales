import { useSearchParams } from 'react-router-dom';
import { MotorConfigScreen } from './MotorConfigScreen';
import { EventConfigPage } from '../../../pages/EventConfigPage';
import { ObservationsScreen } from './ObservationsScreen';
import { ObservationProtocolManagementScreen } from './ObservationProtocolManagementScreen';
import { AnalyticsScreen } from './AnalyticsScreen';
import { DashboardHeader } from '../components/DashboardHeader';
import { AppFooter } from '@/components/AppFooter';
import { SectionTabs } from '../components/ui';
import { useAppStore } from '@/core/state/store';
import { filterByPermission, useRole } from '@/core/auth/useAuth';

type Section =
  | 'config'
  | 'predictions'
  | 'observations'
  | 'observation-protocols'
  | 'analytics';

const SECTIONS: { key: Section; label: string; permission?: string }[] = [
  // El permiso va en la definición de la pestaña, no en un if dentro del render:
  // así la lista visible y la regla de acceso viven en el mismo lugar, y no puede
  // quedar una pestaña visible que el backend le va a responder 403.
  //
  // Antes no había `permission` en ninguna: las cinco pestañas se mostraban a
  // cualquier usuario con token, incluido un operador de campo.
  { key: 'config', label: 'Configuración', permission: 'config:read' },
  { key: 'predictions', label: 'Predicciones', permission: 'events:read' },
  { key: 'observations', label: 'Observaciones', permission: 'observations:read' },
  // Tab propia y no un bloque dentro de "Observaciones": la de al lado es la
  // carga manual de datos (qué se registró) y esta es la de reglas (cuándo
  // debería registrarse). Mezclarlas hacia que el operador no sepa cual es cual.
  {
    key: 'observation-protocols',
    label: 'Protocolos de observación',
    permission: 'protocols:read',
  },
  { key: 'analytics', label: 'Analytics', permission: 'analytics:read' },
];

// Las claves permitidas ahora dependen de los permisos del usuario y se calculan
// en el componente, así que no hay una constante `SECTION_KEYS` global.

export function MotorScreen() {
  const user = useAppStore((s) => s.auth.user);
  // `useRole('OPERADOR_CAMPO')` devuelve un booleano. Antes se llamaba sin
  // argumentos y se comparaba contra el string, así que la comparación era
  // siempre falsa y el filtro de abajo no filtraba nada.
  const esOperadorCampo = useRole('OPERADOR_CAMPO');

  // Se recalcula en cada render del store: si cambian los permisos (el admin se
  // los quita mientras la pantalla está abierta), las pestañas se actualizan.
  let seccionesVisibles = filterByPermission(SECTIONS, user);

  // Restricción explícita para OPERADOR_CAMPO: únicamente observaciones.
  // Hoy `events:read` ya no alcanza el rol, así que la pestaña de predicciones
  // cae sola por el filtro de permisos; esto la vuelve a esconder aunque alguien
  // le devuelva ese permiso, que es la intención original de la línea.
  if (esOperadorCampo) {
    seccionesVisibles = seccionesVisibles.filter((s) => s.key === 'observations');
  }
  const clavesVisibles = seccionesVisibles.map((s) => s.key);

  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get('tab') as Section | null;

  // Si la pestaña de la URL ya no está permitida —típico cuando un operador abre
  // un link directo— cae a la primera visible en vez de dejar un 403 en pantalla.
  const activaPorUrl = tabParam && clavesVisibles.includes(tabParam) ? tabParam : null;
  const activeSection: Section =
    activaPorUrl ?? (clavesVisibles[0] as Section | undefined) ?? 'config';

  const selectSection = (section: Section) => {
    setSearchParams({ tab: section });
  };

  if (seccionesVisibles.length === 0) {
    return (
      <div className="min-h-screen bg-slate-50 w-full">
        <DashboardHeader title="Motor" subtitle="Configuración y Análisis del Motor" />
        <p className="p-6 text-sm text-slate-500">
          No tenés permisos para ver ninguna sección del motor.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <DashboardHeader title="Motor" subtitle="Configuración y Análisis del Motor" />
      <SectionTabs
        sections={seccionesVisibles}
        activeSection={activeSection}
        onChange={selectSection}
        className="flex flex-wrap gap-2 px-4 sm:px-6 py-3"
      />

      <main className="p-4 sm:p-6">
        {activeSection === 'config' && <MotorConfigScreen />}
        {activeSection === 'predictions' && <EventConfigPage />}
        {activeSection === 'observations' && <ObservationsScreen />}
        {activeSection === 'observation-protocols' && (
          <ObservationProtocolManagementScreen />
        )}
        {activeSection === 'analytics' && <AnalyticsScreen />}
      </main>

      <AppFooter variant="private" />
    </div>
  );
}