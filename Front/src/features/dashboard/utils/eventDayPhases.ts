import type { OperationalPhaseDTO, EventDayPhaseCreatePayload } from '../types';

export function buildPhasesForProfile(
  profileId: string,
  operationalPhases: OperationalPhaseDTO[],
): EventDayPhaseCreatePayload[] {
  return operationalPhases
    .filter((op) => op.operational_profile_id === profileId)
    .slice()
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((op) => ({
      operational_phase_id: op.id,
      start_min: null,
      end_min: null,
    }));
}

export function allPhasesBelongToProfile(
  phases: { operational_phase_id: string }[],
  operationalPhases: OperationalPhaseDTO[],
): boolean {
  const profileIds = new Set(operationalPhases.map((op) => op.id));
  return phases.every((p) => profileIds.has(p.operational_phase_id));
}