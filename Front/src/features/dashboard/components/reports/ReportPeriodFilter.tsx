import type { ReportPeriodMode } from '../../utils/eventDayPeriod';
import type { EventDaySummary } from '../../types';
import { DEFAULT_TIMEZONE } from './reportFormat';

/**
 * Selector de período de los informes.
 *
 * Vive fuera de `MunicipalReportScreen` a propósito: el estado que produce
 * estaba en ese componente, que se desmonta al cambiar de tab. Con el estado
 * acá arriba (`ReportsScreen`), cambiar de tab no lo destruye y todos los
 * informes reciben el mismo período.
 */
export interface ReportPeriodSelection {
  mode: ReportPeriodMode;
  eventDayDate: string;
  customStart: string;
  customEnd: string;
}

export interface ReportPeriodFilterProps {
  selection: ReportPeriodSelection;
  onChange: (next: ReportPeriodSelection) => void;
  eventDays: EventDaySummary[];
  loadingDays: boolean;
  customRangeInvalid: boolean;
  selectionIncomplete: boolean;
}

const controlClass =
  'w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:border-indigo-500';
const labelClass = 'block text-xs font-semibold text-slate-600 mb-1';

export function ReportPeriodFilter({
  selection,
  onChange,
  eventDays,
  loadingDays,
  customRangeInvalid,
  selectionIncomplete,
}: ReportPeriodFilterProps) {
  const { mode, eventDayDate, customStart, customEnd } = selection;

  const selectionText =
    mode === 'dia'
      ? eventDayDate
        ? `Día operativo ${eventDayDate.split('-').reverse().join('/')}`
        : 'Día operativo (sin elegir)'
      : mode === 'personalizado'
        ? customStart && customEnd
          ? `Rango ${customStart} – ${customEnd}`
          : customStart
            ? `Desde ${customStart} (sin fecha final)`
            : customEnd
              ? `Hasta ${customEnd} (sin fecha inicial)`
              : 'Período personalizado (incompleto)'
        : 'Período del evento';

  return (
    <div className="print:hidden mb-4 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-56">
          <label className={labelClass} htmlFor="period-mode">
            Período del informe
          </label>
          <select
            id="period-mode"
            className={controlClass}
            value={mode}
            onChange={(e) => onChange({ ...selection, mode: e.target.value as ReportPeriodMode })}
          >
            <option value="evento">Período del evento</option>
            <option value="dia">Día operativo</option>
            <option value="personalizado">Período personalizado</option>
          </select>
        </div>

        {mode === 'dia' && (
          <div className="w-56">
            <label className={labelClass} htmlFor="period-event-day">
              Jornada
            </label>
            <select
              id="period-event-day"
              className={controlClass}
              value={eventDayDate}
              onChange={(e) => onChange({ ...selection, eventDayDate: e.target.value })}
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

        {mode === 'personalizado' && (
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
                onChange={(e) => onChange({ ...selection, customStart: e.target.value })}
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
                onChange={(e) => onChange({ ...selection, customEnd: e.target.value })}
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
          El rango es inválido: la fecha final es anterior a la inicial. Se mantiene el período
          del evento.
        </p>
      )}

      {selectionIncomplete && !customRangeInvalid && (
        <p className="mt-3 text-xs text-amber-700">
          No hay un período seleccionado para analizar. Mientras no completes la selección, los
          informes usan el período del evento.
        </p>
      )}
    </div>
  );
}
