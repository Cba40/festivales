export interface EventDayPeriod {
  start: string;
  end: string;
}

const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;

const partsFormatterCache = new Map<string, Intl.DateTimeFormat>();

function getPartsFormatter(timeZone: string): Intl.DateTimeFormat {
  const cached = partsFormatterCache.get(timeZone);
  if (cached) return cached;
  let formatter: Intl.DateTimeFormat;
  try {
    formatter = new Intl.DateTimeFormat('en-US', {
      timeZone,
      hourCycle: 'h23',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    throw new Error(`Zona horaria inválida: ${timeZone}`);
  }
  partsFormatterCache.set(timeZone, formatter);
  return formatter;
}

/** Desplazamiento de la zona respecto de UTC, en ms, en el instante dado. */
function getTimeZoneOffsetMs(instant: Date, timeZone: string): number {
  const parts = getPartsFormatter(timeZone).formatToParts(instant);
  const field: Record<string, number> = {};
  for (const part of parts) {
    if (part.type !== 'literal') field[part.type] = Number(part.value);
  }
  const asUtc = Date.UTC(
    field.year,
    field.month - 1,
    field.day,
    field.hour,
    field.minute,
    field.second,
  );
  return asUtc - Math.floor(instant.getTime() / 1000) * 1000;
}

/**
 * Instante UTC de una hora de pared local en una zona horaria IANA.
 * Se itera dos veces para resolver bien los bordes de cambio de hora.
 */
function zonedWallTimeToInstant(
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number,
  second: number,
  millisecond: number,
  timeZone: string,
): Date {
  const wallAsUtc = Date.UTC(year, month - 1, day, hour, minute, second, millisecond);
  let instant = new Date(wallAsUtc - getTimeZoneOffsetMs(new Date(wallAsUtc), timeZone));
  const refined = wallAsUtc - getTimeZoneOffsetMs(instant, timeZone);
  if (refined !== instant.getTime()) {
    instant = new Date(refined);
  }
  return instant;
}

function parseEventDayDate(value: string): { year: number; month: number; day: number } {
  const match = DATE_PATTERN.exec(value);
  if (!match) {
    throw new Error(`Fecha de jornada inválida (se espera YYYY-MM-DD): ${value}`);
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const probe = new Date(Date.UTC(year, month - 1, day));
  if (
    probe.getUTCFullYear() !== year ||
    probe.getUTCMonth() !== month - 1 ||
    probe.getUTCDate() !== day
  ) {
    throw new Error(`Fecha de jornada inexistente: ${value}`);
  }
  return { year, month, day };
}

/**
 * Convierte la fecha de una jornada operativa (EventDay.date) en el período
 * start/end queentienden los endpoints de informes.
 *
 * start = 00:00:00.000 local, end = 23:59:59.999 local del mismo día.
 * Devuelve ISO 8601 en UTC. La precisión es de milisegundos (JS Date no
 * representa microsegundos), por lo que el extremo derecho cubre el día
 * completo salvo los últimos 999 microsegundos.
 */
export function eventDayToPeriod(date: string, timeZone: string): EventDayPeriod {
  const { year, month, day } = parseEventDayDate(date);
  const start = zonedWallTimeToInstant(year, month, day, 0, 0, 0, 0, timeZone);
  const end = zonedWallTimeToInstant(year, month, day, 23, 59, 59, 999, timeZone);
  return { start: start.toISOString(), end: end.toISOString() };
}

/**
 * Período personalizado: desde las 00:00:00.000 del primer día local hasta
 * las 23:59:59.999 del último día local, ambos inclusivos.
 */
export function eventDayRangeToPeriod(
  startDate: string,
  endDate: string,
  timeZone: string,
): EventDayPeriod {
  const from = eventDayToPeriod(startDate, timeZone);
  const to = eventDayToPeriod(endDate, timeZone);
  if (Date.parse(to.end) < Date.parse(from.start)) {
    throw new Error(`Rango de fechas inválido: ${startDate} → ${endDate}`);
  }
  return { start: from.start, end: to.end };
}

/** Período acumulado: el contrato de "sin rango" (ausencia de filtro). */
export const ACCUMULATED_PERIOD: Readonly<{ start: null; end: null }> = Object.freeze({
  start: null,
  end: null,
});

export type ReportPeriodMode = 'evento' | 'dia' | 'personalizado';

export type ResolvedReportPeriod = {
  start?: string;
  end?: string;
};

/**
 * Traduce la selección del dashboard a los límites que viajan a los endpoints.
 *
 * Devolver un objeto vacío significa "omitir start/end" y deja que el backend
 * resuelva el período del evento. Eso solo es válido para el modo `evento`: si
 * el usuario eligió un día o un rango, una selección incompleta NO puede caer
 * silenciosamente al período del evento, porque mostraría un período distinto
 * del solicitado. Por eso un extremo suelto se envía como rango abierto, que el
 * backend soporta (`timestamp >= start` o `timestamp <= end`).
 */
export function resolveReportPeriod(
  mode: ReportPeriodMode,
  options: {
    eventDayDate?: string;
    customStart?: string;
    customEnd?: string;
    timeZone: string;
  },
): ResolvedReportPeriod {
  const { eventDayDate = '', customStart = '', customEnd = '', timeZone } = options;

  if (mode === 'evento') return {};

  if (mode === 'dia') {
    if (!eventDayDate) return {};
    return eventDayToPeriod(eventDayDate, timeZone);
  }

  if (customStart && customEnd) {
    return eventDayRangeToPeriod(customStart, customEnd, timeZone);
  }
  if (customStart) {
    return { start: eventDayToPeriod(customStart, timeZone).start };
  }
  if (customEnd) {
    return { end: eventDayToPeriod(customEnd, timeZone).end };
  }
  return {};
}

/** `true` cuando el modo elegido no puede producir un período utilizable. */
export function isIncompleteSelection(
  mode: ReportPeriodMode,
  options: {
    eventDayDate?: string;
    customStart?: string;
    customEnd?: string;
  },
): boolean {
  if (mode === 'evento') return false;
  if (mode === 'dia') return !options.eventDayDate;
  if (options.customStart && options.customEnd) {
    return options.customEnd < options.customStart;
  }
  return !options.customStart && !options.customEnd;
}
