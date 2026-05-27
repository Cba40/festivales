export type SaturationLevel = 'bajo' | 'medio' | 'alto' | 'colapsado';
export type StatusLevel = 'activa' | 'restringida' | 'cerrada';
export type SeverityLevel = 'baja' | 'media' | 'alta';
export type IncidentStatus = 'abierto' | 'en_progreso' | 'resuelto';

export interface Zone {
  id: string;
  name: string;
  type: string;
  saturation: SaturationLevel;
  status: StatusLevel;
  capacity: number;
  availableCapacity: number;
}

export interface Incident {
  id: string;
  type: string;
  severity: SeverityLevel;
  description: string;
  status: IncidentStatus;
  createdAt: string;
  zoneId?: string;
}
