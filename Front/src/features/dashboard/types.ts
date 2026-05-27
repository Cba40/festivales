// src/features/dashboard/types.ts

// ============================================
// TIPOS DE DOMINIO — Dashboard Municipal
// Alineados con el modelo de dominio del backend
// ============================================

/** Niveles de saturación territorial */
export type SaturationLevel = 'bajo' | 'medio' | 'alto' | 'colapsado';

/** Tipos de zona operativa */
export type ZoneType =
  | 'estacionamiento'
  | 'transporte'
  | 'comida'
  | 'descanso'
  | 'servicios'
  | 'emergencia';

/** Estado operativo de una zona */
export type ZoneStatus = 'activa' | 'restringida' | 'cerrada';

/** Tipos de incidente operativo */
export type IncidentType = 'congestion' | 'closure' | 'emergency';

/** Niveles de severidad de incidente */
export type IncidentSeverity = 'baja' | 'media' | 'alta' | 'critica';

/** Estado de ciclo de vida de un incidente */
export type IncidentStatus = 'abierto' | 'en_progreso' | 'resuelto';

// ============================================
// INTERFACES PRINCIPALES
// ============================================

/** Zona territorial con métricas operativas */
export interface Zone {
  id: string;
  name: string;
  type: ZoneType;
  saturation: SaturationLevel;
  status: ZoneStatus;
  capacity: number;
  availableCapacity: number;
}

/** Incidente reportado durante la operación */
export interface Incident {
  id: string;
  type: IncidentType;
  severity: IncidentSeverity;
  description: string;
  status: IncidentStatus;
  createdAt: string; // ISO 8601
  zoneId?: string;
}

// ============================================
// DTOs PARA API (placeholder para FastAPI)
// ============================================

/** Payload para actualizar saturación vía PATCH */
export interface UpdateSaturationPayload {
  zoneId: string;
  saturation: SaturationLevel;
}

/** Payload para reportar incidente vía POST */
export interface ReportIncidentPayload {
  type: IncidentType;
  severity: IncidentSeverity;
  description: string;
  zoneId?: string;
}

/** Respuesta genérica de estado del evento */
export interface EventStateResponse {
  zones: Zone[];
  incidents: Incident[];
  timestamp: string;
}
