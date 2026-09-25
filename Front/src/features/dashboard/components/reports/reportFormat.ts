export const SERVICE_CATEGORY_LABELS: Record<string, string> = {
  parking: 'Estacionamiento',
  gastronomy: 'Gastronomía',
  transport: 'Transporte',
  bathroom: 'Baños',
  rest: 'Descanso',
  health: 'Salud',
  hydration: 'Hidratación',
  accommodation: 'Hospedaje',
  emergency: 'Emergencias',
  exit: 'Salidas',
  alerts: 'Alertas',
};

export const RESULT_STATUS_LABELS: Record<string, string> = {
  ok: 'Con resultados',
  empty: 'Brecha de información',
  unavailable: 'Servicio no disponible',
  error: 'Incidencia técnica',
};

export function serviceLabel(category: string): string {
  return SERVICE_CATEGORY_LABELS[category] ?? category;
}

export function humanize(value: string): string {
  return value.replace(/_/g, ' ');
}

export function formatISODate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('es-AR', { timeZone: 'UTC' });
}

export function formatDateOnly(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('es-AR', { timeZone: 'UTC' });
}

/**
 * Formatea un bucket de `temporal_distribution`.
 *
 * El bucket llega como hora de pared LOCAL ya truncada por
 * `date_trunc(... timestamp AT TIME ZONE ...)` y sin offset. No debe pasar por
 * `new Date()` (lo interpretaría como hora del navegador) ni por
 * `toLocaleString` con `timeZone` (en este runtime `es-AR` no respeta la hora).
 * Se formatea desde sus componentes, sin ninguna conversión: muestra
 * exactamente la hora local con la que se agrupó.
 */
export function formatLocalBucket(value: string): string {
  const parts = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(value);
  if (!parts) return value;
  return `${parts[3]}/${parts[2]}/${parts[1]} ${parts[4]}:${parts[5]}`;
}

/**
 * Formatea un instante absoluto como fecha de la zona horaria operacional.
 *
 * El backend devuelve los límites del período como instantes UTC. Mostrarlos
 * con UTC mostraría el día equivocado: el fin de la jornada del 21/07 llega como
 * 22/07T02:59Z y se vería como 22/07. Se leen solo las partes de fecha, sin
 * la hora, para no depender del formato de hora del runtime.
 */
export function formatLocalDate(value: string, timeZone: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date);
  const field: Record<string, string> = {};
  for (const part of parts) {
    if (part.type !== 'literal') field[part.type] = part.value;
  }
  return `${field.day}/${field.month}/${field.year}`;
}

/**
 * Fecha y hora de un instante en la zona horaria operacional (DD/MM/AAAA HH:MM).
 *
 * No se usa `toLocaleString`: en este runtime el locale `es-AR` renderiza las
 * horas >= 13 como 12 h sin el marcador AM/PM (23:30Z se ve "08:30"), y
 * agregar `timeZone` no lo corrige. `formatToParts` con `hourCycle: 'h23'`
 * devuelve las partes sin ambiguüedad.
 */
export function formatLocalDateTime(value: string | Date, timeZone: string): string {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    hourCycle: 'h23',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).formatToParts(date);
  const field: Record<string, string> = {};
  for (const part of parts) {
    if (part.type !== 'literal') field[part.type] = part.value;
  }
  return `${field.day}/${field.month}/${field.year} ${field.hour}:${field.minute}`;
}

export function percentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function phaseDisplayName(name: string): string {
  return name === 'unassigned' ? 'Sin fase asignada' : name;
}

export const DEFAULT_TIMEZONE = 'America/Argentina/Buenos_Aires';