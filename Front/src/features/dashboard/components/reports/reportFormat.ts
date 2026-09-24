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

export function percentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function phaseDisplayName(name: string): string {
  return name === 'unassigned' ? 'Sin fase asignada' : name;
}

export const DEFAULT_TIMEZONE = 'America/Argentina/Buenos_Aires';