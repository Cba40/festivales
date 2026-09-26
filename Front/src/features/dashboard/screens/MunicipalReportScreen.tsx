import { useEffect, useMemo, useState } from 'react';
import { Printer } from 'lucide-react';
import { useEventReport } from '@/hooks/useEventReports';
import { endpoints } from '@/core/api/endpoints';
import { Button } from '../components/ui';
import type { EventDTO, EventSummaryDTO } from '../types';
import { DEFAULT_TIMEZONE, formatLocalDate, formatLocalDateTime } from '../components/reports/reportFormat';
import { useEventDays } from '../hooks/useEventDays';
import {
  isIncompleteSelection,
  resolveReportPeriod,
} from '../utils/eventDayPeriod';
import {
  ReportSummarySection,
  ReportServiceBreakdownSection,
  ReportCoverageGapsSection,
  ReportZoneAnalysisSection,
  ReportTechnicalIncidentsSection,
} from '../components/reports';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

type PeriodMode = 'evento' | 'dia' | 'personalizado';

const PERIOD_MODE_LABELS: Record<string, string> = {
  requested: 'Período seleccionado',
  event: 'Período del evento',
  accumulated: 'Histórico acumulado',
};

const controlClass =
  'w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:border-indigo-500';
const labelClass = 'block text-xs font-semibold text-slate-600 mb-1';

export function MunicipalReportScreen() {
  const [periodMode, setPeriodMode] = useState<PeriodMode>('evento');
  const [eventDayDate, setEventDayDate] = useState('');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  const { eventDays, loading: loadingDays } = useEventDays(EVENT_ID);

  useEffect(() => {
    if (periodMode === 'dia' && !eventDayDate && eventDays.length > 0) {
      setEventDayDate(eventDays[0].date);
    }
  }, [periodMode, eventDayDate, eventDays]);

  const customRangeInvalid =
    periodMode === 'personalizado' && Boolean(customStart) && Boolean(customEnd) && customEnd < customStart;

  // Origen único del período: las siete secciones reciben exactamente estos
  // límites absolutos. Solo el modo "evento" omite start/end; una selección
  // explícita incompleta se envía como rango abierto en vez de caer al período
  // del evento en silencio.
  const period = useMemo(
    () =>
      resolveReportPeriod(periodMode, {
        eventDayDate,
        customStart,
        customEnd,
        timeZone: DEFAULT_TIMEZONE,
      }),
    [periodMode, eventDayDate, customStart, customEnd]
  );

  const selectionIncomplete = isIncompleteSelection(periodMode, {
    eventDayDate,
    customStart,
    customEnd,
  });

  const summary = useEventReport<EventSummaryDTO>(
    EVENT_ID,
    endpoints.reports.summary(EVENT_ID),
    { params: period }
  );
  const eventInfo = useEventReport<EventDTO>(EVENT_ID, endpoints.events.get(EVENT_ID));
  const [generatedAt] = useState(() => new Date());

  const eventName =
    summary.data?.event_name ?? eventInfo.data?.name ?? 'Evento sin identificar';
  const eventDescription = eventInfo.data?.description ?? null;
  const eventLocation = eventInfo.data?.location ?? null;
  const effectivePeriod = summary.data?.period ?? null;
  const effectiveMode = effectivePeriod?.mode ?? null;

  const periodText =
    effectiveMode === 'accumulated'
      ? 'Histórico acumulado (todos los períodos disponibles)'
      : effectivePeriod?.start || effectivePeriod?.end
        ? `${effectivePeriod.start ? formatLocalDate(effectivePeriod.start, DEFAULT_TIMEZONE) : 'inicio no definido'} – ${
            effectivePeriod.end ? formatLocalDate(effectivePeriod.end, DEFAULT_TIMEZONE) : 'fin no definido'
          }`
        : summary.data
          ? 'Período sin definir'
          : '—';

  const selectionText = {
    evento: 'Período del evento',
    dia: eventDayDate
      ? `Día operativo ${eventDayDate.split('-').reverse().join('/')}`
      : 'Día operativo (sin elegir)',
    personalizado: customStart && customEnd
      ? `Rango ${customStart} – ${customEnd}`
      : customStart
        ? `Desde ${customStart} (sin fecha final)`
        : customEnd
          ? `Hasta ${customEnd} (sin fecha inicial)`
          : 'Período personalizado (incompleto)',
  }[periodMode];

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
        <div className="print:hidden mb-4 rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="w-56">
              <label className={labelClass} htmlFor="period-mode">
                Período del informe
              </label>
              <select
                id="period-mode"
                className={controlClass}
                value={periodMode}
                onChange={(e) => setPeriodMode(e.target.value as PeriodMode)}
              >
                <option value="evento">Período del evento</option>
                <option value="dia">Día operativo</option>
                <option value="personalizado">Período personalizado</option>
              </select>
            </div>

            {periodMode === 'dia' && (
              <div className="w-56">
                <label className={labelClass} htmlFor="period-event-day">
                  Jornada
                </label>
                <select
                  id="period-event-day"
                  className={controlClass}
                  value={eventDayDate}
                  onChange={(e) => setEventDayDate(e.target.value)}
                  disabled={loadingDays || eventDays.length === 0}
                >
                  {eventDays.length === 0 && (
                    <option value="">{loadingDays ? 'Cargando…' : 'Sin jornadas'}</option>
                  )}
                  {eventDays.map((day) => (
                    <option key={day.id} value={day.date}>
                      {day.date} · {day.day_of_week}
                      {day.is_active ? '' : ' (inactiva)'}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {periodMode === 'personalizado' && (
              <>
                <div className="w-44">
                  <label className={labelClass} htmlFor="period-start">
                    Desde
                  </label>
                  <input
                    id="period-start"
                    type="date"
                    className={controlClass}
                    value={customStart}
                    onChange={(e) => setCustomStart(e.target.value)}
                  />
                </div>
                <div className="w-44">
                  <label className={labelClass} htmlFor="period-end">
                    Hasta
                  </label>
                  <input
                    id="period-end"
                    type="date"
                    className={controlClass}
                    value={customEnd}
                    onChange={(e) => setCustomEnd(e.target.value)}
                  />
                </div>
              </>
            )}

            <p className="text-xs text-slate-500 pb-2">
              Selección: {selectionText}. Zona horaria: {DEFAULT_TIMEZONE}.
            </p>
          </div>

          {customRangeInvalid && (
            <p className="mt-3 text-xs text-red-600">
              El rango es inválido: la fecha final es anterior a la inicial. Se mantiene el
              período del evento.
            </p>
          )}

          {selectionIncomplete && !customRangeInvalid && (
            <p className="mt-3 text-xs text-amber-700">
              No hay un período seleccionado para analizar. Mientras no completes la
              selección, los informes usan el período del evento.
            </p>
          )}
        </div>

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
              <dd className="text-slate-700">
                {periodText}
                {effectiveMode && effectiveMode !== 'accumulated' && (
                  <span className="ml-2 text-xs text-slate-500">
                    ({PERIOD_MODE_LABELS[effectiveMode] ?? effectiveMode})
                  </span>
                )}
              </dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-slate-500 w-28 shrink-0">Fecha de generación</dt>
              <dd className="text-slate-700">
                {formatLocalDateTime(generatedAt, DEFAULT_TIMEZONE)}
              </dd>
            </div>
          </dl>
        </header>

        <div className="space-y-4">
          <ReportSummarySection start={period.start} end={period.end} />
          <ReportServiceBreakdownSection start={period.start} end={period.end} />
          <ReportZoneAnalysisSection start={period.start} end={period.end} />
          <ReportTechnicalIncidentsSection start={period.start} end={period.end} />
          <ReportCoverageGapsSection start={period.start} end={period.end} />
        </div>

        <footer className="mt-8 pt-4 border-t border-slate-300 text-xs text-slate-500">
          Informe generado el {formatLocalDateTime(generatedAt, DEFAULT_TIMEZONE)} · CBA 4.0
        </footer>
      </div>
    </div>
  );
}