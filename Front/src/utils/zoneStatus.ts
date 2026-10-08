/**
 * Utilidades para el estado de zona (`ZoneStatus`).
 *
 * Centraliza el mapeo de estado -> (color, label, icono) para que todas las
 * pantallas usen la misma convención visual.
 *
 * Valores canónicos definidos en `ZoneStatus` (alineado con `ZoneStatus` del backend).
 */

/** Estados canónicos de zona. */
export type ZoneStatus = 'activa' | 'restringida' | 'alerta' | 'cerrada';

/** Estilo de badge para un estado. */
export interface EstadoStyles {
  /** Clases Tailwind para el badge (bg, text, etc.). */
  className: string;
  /** Etiqueta legible para humanos. */
  label: string;
  /** Icono opcional (nombre de Lucide o componente). */
  icon?: string;
}

/**
 * Mapea un estado canónico a su representación visual.
 *
 * @param status - Estado de zona (`activa` | `restringida` | `alerta` | `cerrada`).
 * @returns Objeto con `className`, `label` e `icon` opcional.
 */
export function getEstadoStyles(status: ZoneStatus): EstadoStyles {
  switch (status) {
    case 'activa':
      return {
        className: 'bg-success/20 text-success',
        label: 'Activa',
        icon: 'CheckCircle2',
      };
    case 'restringida':
      return {
        className: 'bg-warning/20 text-warning',
        label: 'Restringida',
        icon: 'AlertTriangle',
      };
    case 'alerta':
      return {
        className: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
        label: 'Alerta',
        icon: 'AlertTriangle',
      };
    case 'cerrada':
      return {
        className: 'bg-danger/20 text-danger',
        label: 'Cerrada',
        icon: 'XCircle',
      };
  }
}

/**
 * Devuelve solo la etiqueta legible para un estado.
 */
export function getEstadoLabel(status: ZoneStatus): string {
  return getEstadoStyles(status).label;
}

/**
 * Devuelve solo las clases Tailwind para el badge.
 */
export function getEstadoClassName(status: ZoneStatus): string {
  return getEstadoStyles(status).className;
}

/**
 * Normaliza un valor de string crudo (p.ej. del backend legacy) al tipo
 * `ZoneStatus` canónico. Desconocidos -> `undefined`.
 */
export function normalizeZoneStatus(raw: string | null | undefined): ZoneStatus | undefined {
  if (!raw) return undefined;
  const normalized = raw.trim().toLowerCase();
  const mapping: Record<string, ZoneStatus> = {
    'activa': 'activa',
    'active': 'activa',
    'restringida': 'restringida',
    'restricted': 'restringida',
    'con_limites': 'restringida',
    'con_límites': 'restringida',
    'alerta': 'alerta',
    'alert': 'alerta',
    'warning': 'alerta',
    'cerrada': 'cerrada',
    'cerrado': 'cerrada',
    'closed': 'cerrada',
    'canceled': 'cerrada',
    'cancelled': 'cerrada',
  };
  return mapping[normalized];
}