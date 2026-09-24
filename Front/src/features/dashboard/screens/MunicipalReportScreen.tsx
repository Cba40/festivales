import { useState } from 'react';
import { Printer } from 'lucide-react';
import { useEventReport } from '@/hooks/useEventReports';
import { endpoints } from '@/core/api/endpoints';
import { Button } from '../components/ui';
import type { EventDTO, EventSummaryDTO } from '../types';
import { formatDateOnly } from '../components/reports/reportFormat';
import {
  ReportSummarySection,
  ReportServiceBreakdownSection,
  ReportCoverageGapsSection,
  ReportTemporalDistributionSection,
  ReportRecommendedZonesSection,
  ReportTechnicalIncidentsSection,
  ReportOperationalProfileSection,
} from '../components/reports';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function MunicipalReportScreen() {
  const summary = useEventReport<EventSummaryDTO>(
    EVENT_ID,
    endpoints.reports.summary(EVENT_ID)
  );
  const eventInfo = useEventReport<EventDTO>(EVENT_ID, endpoints.events.get(EVENT_ID));
  const [generatedAt] = useState(() => new Date());

  const eventName =
    summary.data?.event_name ?? eventInfo.data?.name ?? 'Evento sin identificar';
  const eventDescription = eventInfo.data?.description ?? null;
  const eventLocation = eventInfo.data?.location ?? null;
  const period = summary.data?.period ?? null;

  const periodText = period?.start || period?.end
    ? `${period.start ? formatDateOnly(period.start) : 'inicio no definido'} – ${
        period.end ? formatDateOnly(period.end) : 'fin no definido'
      }`
    : summary.data
      ? 'Sin actividad registrada en el período'
      : '—';

  return (
    <div className="w-full">
      <div className="print:hidden mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-500">
          Vista institucional lista para impresión: agrupa los informes del evento en un
          único documento. La impresión se ejecuta desde el navegador.
        </p>
        <Button variant="primary" onClick={() => window.print()}>
          <Printer className="w-4 h-4" />
          Imprimir informe
        </Button>
      </div>

      <div className="informe-imprimible">
        <header className="border-b-2 border-slate-800 pb-4 mb-6">
          <h1 className="text-2xl font-bold text-slate-900">Informe del Evento</h1>
          <p className="text-lg font-semibold text-slate-800 mt-1">{eventName}</p>
          {eventDescription && (
            <p className="text-sm text-slate-600 mt-1 max-w-prose">{eventDescription}</p>
          )}

          <dl className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-1.5 text-sm">
            <div className="flex gap-2">
              <dt className="text-slate-500 w-28 shrink-0">ID de evento</dt>
              <dd className="text-slate-700 break-all">{summary.data?.event_id ?? EVENT_ID}</dd>
            </div>
            {eventLocation && (
              <div className="flex gap-2">
                <dt className="text-slate-500 w-28 shrink-0">Ubicación</dt>
                <dd className="text-slate-700">{eventLocation}</dd>
              </div>
            )}
            <div className="flex gap-2">
              <dt className="text-slate-500 w-28 shrink-0">Período analizado</dt>
              <dd className="text-slate-700">{periodText}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-slate-500 w-28 shrink-0">Fecha de generación</dt>
              <dd className="text-slate-700">{generatedAt.toLocaleString('es-AR')}</dd>
            </div>
          </dl>
        </header>

        <div className="space-y-4">
          <ReportSummarySection />
          <ReportServiceBreakdownSection />
          <ReportCoverageGapsSection />
          <ReportTemporalDistributionSection />
          <ReportRecommendedZonesSection />
          <ReportTechnicalIncidentsSection />
          <ReportOperationalProfileSection />
        </div>

        <footer className="mt-8 pt-4 border-t border-slate-300 text-xs text-slate-500">
          Informe generado el {generatedAt.toLocaleString('es-AR')} · CBA 4.0
        </footer>
      </div>
    </div>
  );
}