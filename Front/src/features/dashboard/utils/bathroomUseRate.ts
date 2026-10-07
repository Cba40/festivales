/**
 * Helpers compartidos para `bathroom_use_rate_per_person_hour` (tasa de uso de
 * baños, usos/persona-hora).
 *
 * El campo vive en `service_configs`, a nivel del default global por
 * (zone_type_id, subtipo). Los tres formularios que lo editan
 * (CreateZoneForm, ZoneConfigModal y ServiceConfigForm) leen y escriben la
 * MISMA fila vía `fetchDefaultServiceConfig`, así que quedan sincronizados por
 * construcción. Estas funciones centralizan la detección de bathrooms y la
 * validación para que las tres pantallas se comporten igual.
 *
 * Contrato (ver `app/api/routes/service_configs.py` y el CHECK de la tabla):
 * solo aplica a `subtipo = 'banos'` y debe ser >= 0.
 */

/** Slug canónico del subtipo de baños en el catálogo `zone_subtypes`. */
export const BATHROOM_SUBTIPO = 'banos';

/** Mismo default que `INITIAL_BATHROOM_USE_RATE_PER_PERSON_HOUR` en el backend. */
export const INITIAL_BATHROOM_USE_RATE_PERSON_HOUR = 0.1;

/** Texto de ayuda: deja explícito que 0.1 es hipótesis, no dato medido. */
export const BATHROOM_USE_RATE_HELP =
  'Hipótesis inicial: 0.1. Calibrar con observaciones reales; no es un valor empírico validado. Máximo 2 decimales.';

/** Evita notación científica y coma decimal; exige 0, 1 o 2 decimales. */
const USE_RATE_PATTERN = /^\d+(\.\d{1,2})?$/;

/** ¿El subtipo corresponde a baños? Tolerante a mayúsculas y espacios. */
export function isBathroomSubtipo(subtipo: string | null | undefined): boolean {
  return (subtipo ?? '').trim().toLowerCase() === BATHROOM_SUBTIPO;
}

/**
 * Valor a mostrar en el input: el persistido si existe, si no el default.
 * Evita mostrar un input vacío cuando la fila aún no tiene tasa.
 */
export function formatUseRate(value: number | null | undefined): string {
  return (value ?? INITIAL_BATHROOM_USE_RATE_PERSON_HOUR).toString();
}

export type UseRateParseResult =
  | { ok: true; value: number }
  | { ok: false; error: string };

/**
 * Valida el texto del input. Acepta `0`, decimales de 1 o 2 cifras y rechaza
 * negativos, notación científica, `NaN`, `Infinity` y más de 2 decimales.
 */
export function parseBathroomUseRate(raw: string): UseRateParseResult {
  const trimmed = raw.trim();
  if (trimmed === '') {
    return {
      ok: false,
      error: 'La tasa de uso (usos/persona-hora) es obligatoria para el subtipo "banos"',
    };
  }
  if (!USE_RATE_PATTERN.test(trimmed)) {
    return {
      ok: false,
      error:
        'La tasa de uso debe ser un número mayor o igual a 0 con máximo 2 decimales (ej: 0.1, 0.25)',
    };
  }
  const value = Number(trimmed);
  // Cubre dígitos en exceso (ej: "999...") que Number() reporta como Infinity.
  if (!Number.isFinite(value) || value < 0) {
    return {
      ok: false,
      error:
        'La tasa de uso debe ser un número mayor o igual a 0 con máximo 2 decimales (ej: 0.1, 0.25)',
    };
  }
  return { ok: true, value };
}