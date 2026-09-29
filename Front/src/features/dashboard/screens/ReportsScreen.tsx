import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { SectionTabs } from '../components/ui';
import { DashboardHeader } from '../components/DashboardHeader';
import { AppFooter } from '@/components/AppFooter';
import { ReportPeriodFilter } from '../components/reports/ReportPeriodFilter';
import type { ReportPeriodSelection } from '../components/reports/ReportPeriodFilter';
import { useEventDays } from '../hooks/useEventDays';
import {
  isIncompleteSelection,
  resolveReportPeriod,
  type ReportPeriodMode,
} from '../utils/eventDayPeriod';
import { DEFAULT_TIMEZONE } from '../components/reports/reportFormat';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

type Section =
  | 'reporte'
  | 'summary'
  | 'services'
  | 'coverage'
  | 'temporal'
  | 'zones'
  | 'incidents'
  | 'operational';

interface ReportPeriodProps {
  start?: string;
  end?: string;
}

/** Todos los informes aceptan el mismo par de límites absolutos. */
type ReportSectionComponent = React.LazyExoticComponent<
  React.ComponentType<ReportPeriodProps>
>;

const SECTIONS: { key: Section; label: string; Component: ReportSectionComponent }[] =
  [
    {
      key: 'reporte',
      label: 'Informe del Evento',
      Component: lazy(() =>
        import('@/features/dashboard/screens/MunicipalReportScreen').then((m) => ({
          default: m.MunicipalReportScreen,
        }))
      ),
    },
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
  const [activeSection, setActiveSection] = useState<Section>('reporte');
  const ActiveSectionComponent = SECTIONS.find((s) => s.key === activeSection)?.Component;

  // El período vive acá y no dentro de un informe: antes vivía en
  // MunicipalReportScreen, que se desmonta al cambiar de tab, así que la
  // selección se perdía. Ahora sobrevive al cambio de tab y además la
  // comparten los ocho informes, que antes la recibían como `undefined` y
  // consultaban sin rango.
  const [selection, setSelection] = useState<ReportPeriodSelection>({
    mode: 'evento' as ReportPeriodMode,
    eventDayDate: '',
    customStart: '',
    customEnd: '',
  });

  const { eventDays, loading: loadingDays } = useEventDays(EVENT_ID);

  useEffect(() => {
    if (selection.mode === 'dia' && !selection.eventDayDate && eventDays.length > 0) {
      setSelection((prev) => ({ ...prev, eventDayDate: eventDays[0].date }));
    }
  }, [selection.mode, selection.eventDayDate, eventDays]);

  const period = useMemo(
    () =>
      resolveReportPeriod(selection.mode, {
        eventDayDate: selection.eventDayDate,
        customStart: selection.customStart,
        customEnd: selection.customEnd,
        timeZone: DEFAULT_TIMEZONE,
      }),
    [selection.mode, selection.eventDayDate, selection.customStart, selection.customEnd]
  );

  const customRangeInvalid =
    selection.mode === 'personalizado' &&
    Boolean(selection.customStart) &&
    Boolean(selection.customEnd) &&
    selection.customEnd < selection.customStart;

  const selectionIncomplete = isIncompleteSelection(selection.mode, {
    eventDayDate: selection.eventDayDate,
    customStart: selection.customStart,
    customEnd: selection.customEnd,
  });

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <div className="print:hidden">
        <DashboardHeader title="Informes del Evento" />
      </div>
      <div className="px-4 sm:px-6">
        <ReportPeriodFilter
          selection={selection}
          onChange={setSelection}
          eventDays={eventDays}
          loadingDays={loadingDays}
          customRangeInvalid={customRangeInvalid}
          selectionIncomplete={selectionIncomplete}
        />
      </div>
      <SectionTabs
        sections={TABS}
        activeSection={activeSection}
        onChange={setActiveSection}
        className="print:hidden flex flex-wrap gap-2 px-4 sm:px-6 py-3"
      />

      <main className="p-4 sm:p-6">
        <Suspense fallback={<div className="p-6 text-center text-slate-500">Cargando informe…</div>}>
          {ActiveSectionComponent ? (
            <ActiveSectionComponent start={period.start} end={period.end} />
          ) : null}
        </Suspense>
      </main>

      <div className="print:hidden">
        <AppFooter variant="private" />
      </div>
    </div>
  );
}
