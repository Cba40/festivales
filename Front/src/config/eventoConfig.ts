import { getCachedEventDay, getEventDayPeakRange } from '@/utils/contextoEvento';

export type TipoAccion = 'estacionar' | 'salir' | 'emergencia' | 'fallback';

export type FaseEvento = {
  id: string;
  nombre: string;
  rango: [number, number];
  accion: TipoAccion;
  modo: 'guiar' | 'asistir' | 'informar';
};

const fasesPorDefecto: FaseEvento[] = [
  { id: 'llegada', nombre: 'Llegada', rango: [18, 20], accion: 'estacionar', modo: 'guiar' },
  { id: 'pico', nombre: 'Pico de ingreso', rango: [21, 21], accion: 'estacionar', modo: 'guiar' },
  { id: 'dentro', nombre: 'Dentro del evento', rango: [22, 23], accion: 'salir', modo: 'asistir' },
  { id: 'salida', nombre: 'Salida masiva', rango: [0, 2], accion: 'salir', modo: 'guiar' },
];

let cachedFases: FaseEvento[] | null = null;

const generarFasesDesdeEventDay = (): FaseEvento[] => {
  const peak = getEventDayPeakRange();
  const ed = getCachedEventDay();
  if (!peak && !ed) return fasesPorDefecto;

  const start = ed?.opening_time ?? 18;
  const end = ed?.closing_time ?? 2;
  const peakStart = peak?.[0] ?? 21;
  const peakEnd = peak?.[1] ?? 21;

  const fases: FaseEvento[] = [];
  const prePeakEnd = Math.max(start, peakStart - 1);

  if (start <= prePeakEnd) {
    fases.push({
      id: 'llegada',
      nombre: 'Llegada',
      rango: [start, prePeakEnd],
      accion: 'estacionar',
      modo: 'guiar',
    });
  }

  fases.push({
    id: 'pico',
    nombre: 'Pico de ingreso',
    rango: [peakStart, peakEnd],
    accion: peakStart >= 21 ? 'salir' : 'estacionar',
    modo: 'guiar',
  });

  const postPeakStart = peakEnd + 1;
  if (postPeakStart <= end || (end < start && postPeakStart <= 23)) {
    fases.push({
      id: 'dentro',
      nombre: 'Dentro del evento',
      rango: [postPeakStart, end >= start ? end : 23],
      accion: 'salir',
      modo: 'asistir',
    });
  }

  if (end < start) {
    fases.push({
      id: 'salida',
      nombre: 'Salida masiva',
      rango: [0, end],
      accion: 'salir',
      modo: 'guiar',
    });
  }

  return fases;
};

export const recargarFases = () => {
  cachedFases = generarFasesDesdeEventDay();
};

export const fases = (): FaseEvento[] => {
  if (!cachedFases) {
    cachedFases = generarFasesDesdeEventDay();
  }
  return cachedFases;
};

export const getFaseActual = (hora: number): FaseEvento | undefined => {
  return fases().find((f) => {
    const [inicio, fin] = f.rango;
    if (inicio <= fin) {
      return hora >= inicio && hora <= fin;
    }
    return hora >= inicio || hora <= fin;
  });
};

export const getEventoConfig = () => ({
  estacionamiento: {
    colapsadoThreshold: 10,
    criticoThreshold: 15,
  },
});
