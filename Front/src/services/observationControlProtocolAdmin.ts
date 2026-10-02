import { apiClient } from '@/core/api/client'
import { endpoints } from '@/core/api/endpoints'

/** Métricas que el motor ya publica por zona. Ver `ZoneState` en el backend. */
export type TriggerMetric =
  | 'saturation_level'
  | 'availability'
  | 'estimated_wait'
  | 'confidence'
  | 'projected_density'

export type TriggerOperator = 'gt' | 'gte' | 'lt' | 'lte'

export interface ObservationProtocolDTO {
  id: string
  event_id: string
  event_day_id: string | null
  name: string
  description: string | null
  trigger_metric: TriggerMetric
  trigger_operator: TriggerOperator
  threshold_value: string
  action_interval_minutes: number
  zone_type_id: string | null
  active: boolean
  order: number
}

export interface ObservationProtocolCreateDTO {
  event_id: string
  event_day_id?: string | null
  name: string
  description?: string | null
  trigger_metric: TriggerMetric
  trigger_operator: TriggerOperator
  threshold_value: string
  action_interval_minutes: number
  zone_type_id?: string | null
  active: boolean
  order: number
}

export interface ObservationProtocolUpdateDTO {
  event_day_id?: string | null
  name?: string
  description?: string | null
  trigger_metric?: TriggerMetric
  trigger_operator?: TriggerOperator
  threshold_value?: string
  action_interval_minutes?: number
  zone_type_id?: string | null
  active?: boolean
  order?: number
}

export interface ProtocolSuggestionDTO {
  key: string
  name: string
  description: string | null
  trigger_metric: TriggerMetric
  trigger_operator: TriggerOperator
  threshold_value: string
  action_interval_minutes: number
  rule_sentence: string
}

export interface ComplianceAlertDTO {
  protocol_id: string
  protocol_name: string
  event_day_id: string | null
  zone_id: string | null
  zone_name: string | null
  trigger_metric: TriggerMetric
  trigger_operator: TriggerOperator
  threshold_value: string
  current_value: string | null
  action_interval_minutes: number
  minutes_since_last_observation: number | null
  overdue_minutes: number
  severity: 'critical' | 'warning'
  detail: string
}

export interface ComplianceDTO {
  event_id: string
  evaluated_at: string
  /**
   * Cuántos protocolos llegaron a compararse contra una predicción real. Si es
   * 0, `total_alerts === 0` NO significa que todo cumpla: significa que no
   * había datos para juzgarlo (el Context Engine no publicó predicciones para
   * la jornada). La UI tiene que diferenciar los dos casos.
   */
  protocols_evaluated: number
  total_alerts: number
  alerts: ComplianceAlertDTO[]
}

export interface ApplySuggestionsResultDTO {
  created: number
  skipped: number
  created_names: string[]
}

export async function listProtocols(
  eventId: string,
  includeInactive = false
): Promise<ObservationProtocolDTO[]> {
  const { data } = await apiClient.get<ObservationProtocolDTO[]>(
    endpoints.observationControlProtocolAdmin.list(eventId),
    { params: { include_inactive: includeInactive } }
  )
  return data
}

export async function createProtocol(
  payload: ObservationProtocolCreateDTO
): Promise<ObservationProtocolDTO> {
  const { data } = await apiClient.post<ObservationProtocolDTO>(
    endpoints.observationControlProtocolAdmin.create(),
    payload
  )
  return data
}

export async function updateProtocol(
  id: string,
  payload: ObservationProtocolUpdateDTO
): Promise<ObservationProtocolDTO> {
  const { data } = await apiClient.put<ObservationProtocolDTO>(
    endpoints.observationControlProtocolAdmin.update(id),
    payload
  )
  return data
}

export async function deleteProtocol(id: string): Promise<void> {
  await apiClient.delete(endpoints.observationControlProtocolAdmin.remove(id))
}

export async function getSuggestions(): Promise<ProtocolSuggestionDTO[]> {
  const { data } = await apiClient.get<{ suggestions: ProtocolSuggestionDTO[] }>(
    endpoints.observationControlProtocolAdmin.suggestions()
  )
  return data.suggestions
}

export async function applySuggestions(
  eventId: string,
  suggestionKeys: string[]
): Promise<ApplySuggestionsResultDTO> {
  const { data } = await apiClient.post<ApplySuggestionsResultDTO>(
    endpoints.observationControlProtocolAdmin.applySuggestions(),
    { event_id: eventId, suggestion_keys: suggestionKeys }
  )
  return data
}

export async function getCompliance(eventId: string): Promise<ComplianceDTO> {
  const { data } = await apiClient.get<ComplianceDTO>(
    endpoints.observationControlProtocolAdmin.compliance(eventId)
  )
  return data
}

// ── Etiquetas en español ───────────────────────────────────────────────────
// Los enums del backend son claves tecnicas; el operador municipal nunca deberia
// verlas. Estas tablas son la unica fuente de la traduccion.

export const METRIC_LABELS: Record<TriggerMetric, string> = {
  saturation_level: 'la saturación',
  availability: 'la disponibilidad',
  estimated_wait: 'la espera estimada',
  confidence: 'la confianza del motor',
  projected_density: 'la densidad proyectada',
}

export const METRIC_OPTIONS: { value: TriggerMetric; label: string }[] = [
  { value: 'saturation_level', label: 'La saturación de la zona' },
  { value: 'estimated_wait', label: 'La espera estimada' },
  { value: 'availability', label: 'La disponibilidad de personas' },
  { value: 'projected_density', label: 'La densidad proyectada' },
  { value: 'confidence', label: 'La confianza del motor' },
]

export const OPERATOR_LABELS: Record<TriggerOperator, string> = {
  gt: 'supera',
  gte: 'supera o iguala',
  lt: 'es menor que',
  lte: 'es menor o igual que',
}

export interface ThresholdOption {
  operator: TriggerOperator
  value: string
  label: string
}

/**
 * Valores prellenados por métrica.
 *
 * Las métricas no son homogéneas: `saturation_level` es un ratio 0..1 y
 * `estimated_wait` son minutos. Un `<input type="number">` suelto haría que el
 * operador escribiera `80` cuando la regla espera `0.8`. Por eso el umbral es un
 * dropdown que fija operador y valor juntos.
 */
export const THRESHOLD_OPTIONS: Record<TriggerMetric, ThresholdOption[]> = {
  saturation_level: [
    { operator: 'gt', value: '0.60', label: 'supera 60%' },
    { operator: 'gt', value: '0.70', label: 'supera 70%' },
    { operator: 'gt', value: '0.80', label: 'supera 80%' },
    { operator: 'gt', value: '0.90', label: 'supera 90%' },
  ],
  estimated_wait: [
    { operator: 'gt', value: '5', label: 'supera 5 minutos' },
    { operator: 'gt', value: '10', label: 'supera 10 minutos' },
    { operator: 'gt', value: '15', label: 'supera 15 minutos' },
    { operator: 'gt', value: '30', label: 'supera 30 minutos' },
  ],
  availability: [
    { operator: 'lt', value: '50', label: 'es menor que 50' },
    { operator: 'lt', value: '20', label: 'es menor que 20' },
    { operator: 'lt', value: '10', label: 'es menor que 10' },
    { operator: 'lte', value: '0', label: 'es 0 (sin cupo)' },
  ],
  projected_density: [
    { operator: 'gt', value: '50', label: 'supera 50 personas' },
    { operator: 'gt', value: '100', label: 'supera 100 personas' },
    { operator: 'gt', value: '200', label: 'supera 200 personas' },
  ],
  confidence: [
    { operator: 'lt', value: '0.30', label: 'es menor que 30%' },
    { operator: 'lt', value: '0.50', label: 'es menor que 50%' },
    { operator: 'lt', value: '0.70', label: 'es menor que 70%' },
  ],
}

export const INTERVAL_OPTIONS = [1, 2, 5, 10, 15, 30, 60]

export const INTERVAL_LABELS: Record<number, string> = {
  1: 'cada 1 minuto',
  2: 'cada 2 minutos',
  5: 'cada 5 minutos',
  10: 'cada 10 minutos',
  15: 'cada 15 minutos',
  30: 'cada 30 minutos',
  60: 'cada 1 hora',
}

/** Frase en lenguaje natural de la regla, para el preview en vivo. */
export function describeRule(input: {
  trigger_metric: TriggerMetric
  trigger_operator: TriggerOperator
  threshold_value: string
  action_interval_minutes: number
}): string {
  const metrica = METRIC_LABELS[input.trigger_metric] ?? input.trigger_metric
  const operador = OPERATOR_LABELS[input.trigger_operator] ?? input.trigger_operator
  const valor = Number(input.threshold_value)
  const umbral = Number.isFinite(valor) ? formatThreshold(input.trigger_metric, valor) : input.threshold_value
  const cada = INTERVAL_LABELS[input.action_interval_minutes] ?? `cada ${input.action_interval_minutes} minutos`
  return `Si ${metrica} ${operador} ${umbral}, registrar una observación ${cada}.`
}

/** `saturation_level` y `confidence` son ratios: se muestran como porcentaje. */
export function formatThreshold(metric: TriggerMetric, value: number): string {
  if (metric === 'saturation_level' || metric === 'confidence') {
    return `${Math.round(value * 100)}%`
  }
  if (metric === 'estimated_wait') return `${value} min`
  return `${value}`
}

export function formatMetricValue(metric: TriggerMetric, value: string | null): string {
  if (value === null || value === undefined) return 'sin dato'
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return String(value)
  return formatThreshold(metric, numeric)
}