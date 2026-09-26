export const SERVICE_CATEGORY_LABELS: Record<string, string> = {
  parking: 'Estacionamiento',
  cajeros: 'Cajeros',
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

export interface ReportBreakdownService {
  service_category: string;
  total_consultas: number;
}

export interface ReportBreakdownFilter {
  request_mode: string | null;
  total: number;
}

export interface ReportFilterChild {
  key: string;
  label: string;
  total: number;
}

export interface ReportFilterGroup {
  key: string;
  label: string;
  total: number;
  children: ReportFilterChild[];
}

const GENERAL_CATEGORIES = ['bathroom', 'hydration', 'rest', 'cajeros'];
const GENERAL_GROUP_LABEL = 'Servicios Generales';

const FILTER_LABELS: Record<string, string> = {
  'mode=peatonal': 'Peatonal',
  'mode=vehicular': 'Vehicular',
  'mode=transporte': 'Transporte Público',
  'transport_type=urbano': 'Urbano',
  'transport_type=interurbano': 'Interurbano',
  'type=hotel': 'Hotel',
  'type=camping': 'Camping',
  'type=hostel': 'Hostel',
  'type=other': 'Otros',
  'type=all': 'Todos',
  '/estacionar': 'Apertura de Estacionamiento',
  '/emergencia': 'Apertura de Emergencias',
  '/servicios/comer': 'Apertura de Gastronomía',
};

const FILTER_OWNER: Record<string, string> = {
  'mode=peatonal': 'exit',
  'mode=vehicular': 'exit',
  'mode=transporte': 'exit',
  'transport_type=urbano': 'transport',
  'transport_type=interurbano': 'transport',
  'type=hotel': 'accommodation',
  'type=camping': 'accommodation',
  'type=hostel': 'accommodation',
  'type=other': 'accommodation',
  'type=all': 'accommodation',
  '/estacionar': 'parking',
  '/emergencia': 'emergency',
  '/servicios/comer': 'gastronomy',
  'protocolo=': 'emergency',
};

const PROTOCOL_PREFIX = 'protocolo=';
const LEGACY_DESTINATION_GROUP = 'legacy-destinations';
const SALIDA_PATTERN = /^salida_(.+?)=(.+)$/;
const TRANSPORTE_PATTERN = /^transporte_(.+?)=(.+)$/;

const MODALITY_LABELS: Record<string, string> = {
  vehicular: 'Vehicular',
  peatonal: 'Peatonal',
  transporte: 'Transporte Público',
  urbano: 'Urbano',
  interurbano: 'Interurbano',
  todos: 'Todos',
  sin_modo: 'Sin modo',
};

function modalityLabel(value: string): string {
  return MODALITY_LABELS[value] ?? value.charAt(0).toUpperCase() + value.slice(1);
}


const ZONES_GROUP = 'shared-zones';
const UNFILTERED_GROUP = 'unfiltered';

/**
 * Agrupa el desglose plano del backend en una vista jerárquica por categoría.
 *
 * El backend agrupa por `request_mode` sin `service_category`, así que la
 * atribución se deriva de las reglas de emisión del cliente. Dos familias las
 * emiten DOS categorías a la vez (`destination=` en salidas y transporte;
 * `zona=` en estacionamiento y baños) y no se pueden repartir sin inventar el
 * dato: se exponen en grupos compartidos en vez de duplicarlas. Los subtipos de
 * Servicios Generales no se listan aparte porque ya son los hijos del grupo
 * virtual y sumarlos otra vez duplicaría el total.
 */
export function buildFilterGroups(
  services: ReportBreakdownService[],
  filters: ReportBreakdownFilter[] | null | undefined,
  protocolTitles: Record<string, string> = {},
): ReportFilterGroup[] {
  const totalsByCategory = new Map<string, number>();
  for (const service of services ?? []) {
    totalsByCategory.set(service.service_category, service.total_consultas);
  }

  const groups = new Map<string, ReportFilterGroup>();
  const ensureGroup = (key: string, label: string, total: number) => {
    let group = groups.get(key);
    if (!group) {
      group = { key, label, total, children: [] };
      groups.set(key, group);
    }
    return group;
  };

  const generalTotal = GENERAL_CATEGORIES.reduce(
    (sum, category) => sum + (totalsByCategory.get(category) ?? 0),
    0,
  );
  const generalChildren: ReportFilterChild[] = GENERAL_CATEGORIES.filter(
    (category) => totalsByCategory.has(category),
  ).map((category) => ({
    key: category,
    label: SERVICE_CATEGORY_LABELS[category] ?? category,
    total: totalsByCategory.get(category) ?? 0,
  }));

  for (const [category, total] of totalsByCategory) {
    if (GENERAL_CATEGORIES.includes(category)) continue;
    ensureGroup(category, SERVICE_CATEGORY_LABELS[category] ?? category, total);
  }
  if (generalChildren.length > 0) {
    ensureGroup(GENERAL_GROUP_LABEL, GENERAL_GROUP_LABEL, generalTotal).children.push(
      ...generalChildren,
    );
  }

  const shared: Record<string, { label: string }> = {
    [LEGACY_DESTINATION_GROUP]: {
      label: 'Destinos sin atribución (registros previos)',
    },
    [ZONES_GROUP]: { label: 'Zonas (estacionamiento y baños)' },
    [UNFILTERED_GROUP]: { label: 'Sin filtro' },
  };

  for (const filter of filters ?? []) {
    const mode = filter.request_mode;
    if (mode === null || mode === undefined) {
      ensureGroup(UNFILTERED_GROUP, shared[UNFILTERED_GROUP].label, 0).children.push({
        key: 'sin-filtro',
        label: 'Sin filtro',
        total: filter.total,
      });
      continue;
    }
    if (GENERAL_CATEGORIES.includes(mode)) continue;
    if (mode.startsWith('destination=')) {
      // Registros anteriores a los prefijos por modalidad: no se puede saber si
      // pertenecen a Salidas o a Transporte, así que no se atribuyen a ninguna.
      ensureGroup(LEGACY_DESTINATION_GROUP, shared[LEGACY_DESTINATION_GROUP].label, 0).children.push({
        key: mode,
        label: mode.slice('destination='.length),
        total: filter.total,
      });
      continue;
    }
    if (mode.startsWith('zona=')) {
      ensureGroup(ZONES_GROUP, shared[ZONES_GROUP].label, 0).children.push({
        key: mode,
        label: mode.slice('zona='.length),
        total: filter.total,
      });
      continue;
    }
    const salida = SALIDA_PATTERN.exec(mode);
    if (salida) {
      const owner = groups.get('exit');
      if (owner) {
        owner.children.push({
          key: mode,
          label: `${modalityLabel(salida[1])}: ${salida[2]}`,
          total: filter.total,
        });
      }
      continue;
    }
    const transporte = TRANSPORTE_PATTERN.exec(mode);
    if (transporte) {
      const owner = groups.get('transport');
      if (owner) {
        owner.children.push({
          key: mode,
          label: `${modalityLabel(transporte[1])}: ${transporte[2]}`,
          total: filter.total,
        });
      }
      continue;
    }
    const exact = FILTER_LABELS[mode];
    if (exact) {
      const owner = FILTER_OWNER[mode];
      const target = owner ? groups.get(owner) : undefined;
      if (target) {
        target.children.push({ key: mode, label: exact, total: filter.total });
      }
      continue;
    }
    if (mode.startsWith(PROTOCOL_PREFIX)) {
      const owner = groups.get(FILTER_OWNER[PROTOCOL_PREFIX]);
      const id = mode.slice(PROTOCOL_PREFIX.length);
      if (owner) {
        owner.children.push({
          key: mode,
          label: protocolTitles[id] ?? `Protocolo ${id.slice(0, 8)}`,
          total: filter.total,
        });
      }
      continue;
    }
  }

  const result = [...groups.values()].map((group) => {
    if (group.children.length === 0) return group;
    const childTotal = group.children.reduce((sum, child) => sum + child.total, 0);
    return {
      ...group,
      // Un grupo real puede tener hijos que no cubren todo su total (por
      // ejemplo, una apertura de pantalla sin request_mode). El total del
      // grupo sigue siendo el de la categoría; los compartidos se derivan.
      total: shared[group.key] ? childTotal : Math.max(group.total, childTotal),
      children: [...group.children].sort((a, b) => b.total - a.total),
    };
  });

  return result.sort((a, b) => b.total - a.total);
}

export function phaseDisplayName(name: string): string {
  return name === 'unassigned' ? 'Sin fase asignada' : name;
}

export const DEFAULT_TIMEZONE = 'America/Argentina/Buenos_Aires';