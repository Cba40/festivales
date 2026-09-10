import type { EmergencyType } from '../../../services/emergencyAdmin';

export type { EmergencyType };

export const EMERGENCY_TYPE_LABELS: Record<EmergencyType, string> = {
  policia: 'Policía',
  bomberos: 'Bomberos',
  salud: 'Salud',
  defensa_civil: 'Defensa Civil',
  numero_emergencia: 'Número de Emergencia',
  otro: 'Otro',
};
