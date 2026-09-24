import { lazy, Suspense, useState } from 'react';
import { SectionTabs } from '../components/ui';
import { DashboardHeader } from '../components/DashboardHeader';
import { AppFooter } from '@/components/AppFooter';

type Section =
  | 'summary'
  | 'services'
  | 'coverage'
  | 'temporal'
  | 'zones'
  | 'incidents'
  | 'operational';

const SECTIONS: { key: Section; label: string; Component: React.LazyExoticComponent<() => React.JSX.Element> }[] =
  [
    {
      key: 'summary',
      label: 'Resumen',
      Component: lazy(() =>
        import('@/features/dashboard/components/reports/ReportSummarySection').then((m) => ({
          default: m.ReportSummarySection,
        }))
      ),
    },
    {
      key: 'services',
      label: 'Por Servicio',
      Component: lazy(() =>
        import('@/features/dashboard/components/reports/ReportServiceBreakdownSection').then((m) => ({
          default: m.ReportServiceBreakdownSection,
        }))
      ),
    },
    {
      key: 'coverage',
      label: 'Brechas de Información',
      Component: lazy(() =>
        import('@/features/dashboard/components/reports/ReportCoverageGapsSection').then((m) => ({
          default: m.ReportCoverageGapsSection,
        }))
      ),
    },
    {
      key: 'temporal',
      label: 'Distribución Temporal',
      Component: lazy(() =>
        import('@/features/dashboard/components/reports/ReportTemporalDistributionSection').then((m) => ({
          default: m.ReportTemporalDistributionSection,
        }))
      ),
    },
    {
      key: 'zones',
      label: 'Zonas Recomendadas',
      Component: lazy(() =>
        import('@/features/dashboard/components/reports/ReportRecommendedZonesSection').then((m) => ({
          default: m.ReportRecommendedZonesSection,
        }))
      ),
    },
    {
      key: 'incidents',
      label: 'Incidencias Técnicas',
      Component: lazy(() =>
        import('@/features/dashboard/components/reports/ReportTechnicalIncidentsSection').then((m) => ({
          default: m.ReportTechnicalIncidentsSection,
        }))
      ),
    },
    {
      key: 'operational',
      label: 'Perfil Operacional',
      Component: lazy(() =>
        import('@/features/dashboard/components/reports/ReportOperationalProfileSection').then((m) => ({
          default: m.ReportOperationalProfileSection,
        }))
      ),
    },
  ];

const TABS: { key: Section; label: string }[] = SECTIONS.map(({ key, label }) => ({ key, label }));

export function ReportsScreen() {
  const [activeSection, setActiveSection] = useState<Section>('summary');
  const ActiveSectionComponent = SECTIONS.find((s) => s.key === activeSection)?.Component;

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <DashboardHeader title="Informes del Evento" />
      <SectionTabs
        sections={TABS}
        activeSection={activeSection}
        onChange={setActiveSection}
        className="flex flex-wrap gap-2 px-4 sm:px-6 py-3"
      />

      <main className="p-4 sm:p-6">
        <Suspense fallback={<div className="p-6 text-center text-slate-500">Cargando informe…</div>}>
          {ActiveSectionComponent ? <ActiveSectionComponent /> : null}
        </Suspense>
      </main>

      <AppFooter variant="private" />
    </div>
  );
}