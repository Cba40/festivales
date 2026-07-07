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
  lat?: number;
  lng?: number;
  distancia_min?: number;
  espera_min?: number;
  referencia?: string;
  calle?: string;
  disponibilidad?: number;
  subtipo?: string;
  x?: number;
  y?: number;
  transporte?: string;
  capacidad_estimada?: number;
  es_embudo?: boolean;
  direccion?: string;
  horario?: string;
  telefono?: string;
  servicios?: string[];
  posibilidadSentarse?: string;
  tipo_culinario?: string;
  geometry_type?: string;
  coordinates?: unknown;
  descripcion?: string;
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

export interface EventDaySummary {
  id: string;
  date: string;
  day_of_week: string;
  entry_start_time: string;
  entry_peak_start_time: string;
  entry_peak_end_time: string;
  event_start_time: string;
  exit_peak_start_time: string;
  exit_peak_end_time: string;
  event_end_time: string;
  weather: string | null;
  headliner_artist: string | null;
  expected_attendance: number | null;
  is_active: boolean;
}

export interface EventDay {
  id: string;
  event_id: string;
  date: string;
  day_of_week: string;
  entry_start_time: string;
  entry_peak_start_time: string;
  entry_peak_end_time: string;
  event_start_time: string;
  exit_peak_start_time: string;
  exit_peak_end_time: string;
  event_end_time: string;
  weather: string | null;
  headliner_artist: string | null;
  expected_attendance: number | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EventDayCreatePayload {
  date: string;
  day_of_week: string;
  entry_start_time: string;
  entry_peak_start_time: string;
  entry_peak_end_time: string;
  event_start_time: string;
  exit_peak_start_time: string;
  exit_peak_end_time: string;
  event_end_time: string;
  weather?: string | null;
  headliner_artist?: string | null;
  expected_attendance?: number | null;
  notes?: string | null;
  is_active?: boolean;
}
