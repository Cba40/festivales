import type { EventDayPhaseCreatePayload } from '../types';

export interface NormalizedPhase {
  operational_phase_id: string;
  start_min: number | null;
  end_min: number | null;
  intensity: number;
}

const DAY_MINUTES = 1440;

export function minutesToTimeStr(min: number): string {
  const civilMin = ((min % DAY_MINUTES) + DAY_MINUTES) % DAY_MINUTES;
  const h = Math.floor(civilMin / 60).toString().padStart(2, '0');
  const m = (civilMin % 60).toString().padStart(2, '0');
  return `${h}:${m}`;
}

export function timeStrToMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number);
  return h * 60 + m;
}

export function resolveOperationalWindow(
  operationalStartMin: number,
  operationalEndMin: number,
): { start: number; end: number } {
  const end = operationalEndMin <= operationalStartMin
    ? operationalEndMin + DAY_MINUTES
    : operationalEndMin;
  return { start: operationalStartMin, end };
}

export function resolveOperationalMinutes(
  phases: EventDayPhaseCreatePayload[],
  operationalStartMin: number,
  operationalEndMin: number,
  operationalPhases: { id: string; sort_order: number }[],
): NormalizedPhase[] {
  const opWindow = resolveOperationalWindow(operationalStartMin, operationalEndMin);
  const sortedPhases = [...phases].sort((a, b) => {
    const aOp = operationalPhases.find((p) => p.id === a.operational_phase_id);
    const bOp = operationalPhases.find((p) => p.id === b.operational_phase_id);
    return (aOp?.sort_order ?? 0) - (bOp?.sort_order ?? 0);
  });

  let offset = 0;
  let previousEnd = opWindow.start;

  return sortedPhases.map((phase) => {
    if (phase.start_min === null || phase.end_min === null) {
      return { start_min: null, end_min: null, operational_phase_id: phase.operational_phase_id, intensity: phase.intensity };
    }

    let start = phase.start_min + offset;
    let end = phase.end_min + offset;

    if (end <= start) {
      end += DAY_MINUTES;
      offset += DAY_MINUTES;
    }

    if (start < previousEnd) {
      start += DAY_MINUTES;
      end += DAY_MINUTES;
      offset += DAY_MINUTES;
    }

    previousEnd = end;

    return { start_min: start, end_min: end, operational_phase_id: phase.operational_phase_id, intensity: phase.intensity };
  });
}
