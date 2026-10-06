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
import { useAppStore } from '@/core/state/store';

type Section = 'summary' | 'services' | 'zones' | 'census' | 'coverage';

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
      key: 'summary',
      label: 'Resumen de Actividad',
      Component: lazy(() =>
        import('@/features/dashboard/components/reports/ReportSummarySection').then((m) => ({
          default: m.ReportSummarySection,
        }))
      ),
    },
    {
      key: 'services',
      label: 'Actividad por Servicio',
      Component: lazy(() =>
        import('@/features/dashboard/components/reports/ReportServiceBreakdownSection').then((m) => ({
          default: m.ReportServiceBreakdownSection,
        }))
      ),
    },
    {
      key: 'zones',
      label: 'Análisis de Zonas',
      Component: lazy(() =>
        import('@/features/dashboard/components/reports/ReportZoneAnalysisSection').then((m) => ({
          default: m.ReportZoneAnalysisSection,
        }))
      ),
    },
    {
      key: 'census',
      label: 'Censo Operativo',
      Component: lazy(() =>
        import('@/features/dashboard/components/reports/ReportFieldCensusSection').then((m) => ({
          default: m.ReportFieldCensusSection,
        }))
      ),
    },
    {
      key: 'coverage',
      label: 'Cobertura de Datos por Servicio',
      Component: lazy(() =>
        import('@/features/dashboard/components/reports/ReportCoverageGapsSection').then((m) => ({
          default: m.ReportCoverageGapsSection,
        }))
      ),
    },
  ];

const TABS: { key: Section; label: string }[] = SECTIONS.map(({ key, label }) => ({ key, label }));

export function ReportsScreen() {
  // Evento activo del store global (`useActiveEvent`), no `VITE_EVENT_ID`.
  const eventId = useAppStore((s) => s.activeEventId);
  const [activeSection, setActiveSection] = useState<Section>('summary');
  const ActiveSectionComponent = SECTIONS.find((s) => s.key === activeSection)?.Component;

  // El período vive acá y no dentro de un informe: antes vivía en
  // MunicipalReportScreen, que se desmonta al cambiar de tab, así que la
  // selección se perdía. Ahora sobrevive al cambio de tab y además la
  // comparten los cinco informes, que antes la recibían como `undefined` y
  // consultaban sin rango.
  const [selection, setSelection] = useState<ReportPeriodSelection>({
    mode: 'evento' as ReportPeriodMode,
    eventDayDate: '',
    customStart: '',
    customEnd: '',
  });

  const { eventDays, loading: loadingDays } = useEventDays(eventId);

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
