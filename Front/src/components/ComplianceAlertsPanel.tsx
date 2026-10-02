import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, Clock, RefreshCw } from 'lucide-react';
import {
  getCompliance,
  formatMetricValue,
  METRIC_LABELS,
  type ComplianceAlertDTO,
  type ComplianceDTO,
} from '@/services/observationControlProtocolAdmin';
import { Badge } from '@/features/dashboard/components/ui/Badge';
import { Card } from '@/features/dashboard/components/ui/Card';
import { Button } from '@/features/dashboard/components/ui/Button';

const POLL_MS = 30_000;

/**
 * Panel de cumplimiento en tiempo real de los Protocolos de Control de
 * Observaciones.
 *
 * Sondea `/compliance` cada 30 s mientras el componente está montado. El polling
 * se pausa cuando la pestaña está oculta (`visibilitychange`) para no gastar
 * requests contra un endpoint que además está rate limited, y se reanuda al
 * volver. Todas las alertas llegan con `event_id`, así que en este despliegue el
 * endpoint va con `verify_token`.
 */
export function ComplianceAlertsPanel({ eventId }: { eventId: string }) {
  const [data, setData] = useState<ComplianceDTO | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);

  const cargar = useCallback(async () => {
    if (document.visibilityState === 'hidden') return;
    try {
      const respuesta = await getCompliance(eventId);
      setData(respuesta);
      setError(null);
    } catch {
      setError('No se pudo evaluar el cumplimiento de los protocolos.');
    } finally {
      setIsLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    void cargar();
    timerRef.current = window.setInterval(() => void cargar(), POLL_MS);

    const onVisibility = () => {
      if (document.visibilityState === 'visible') void cargar();
    };
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      if (timerRef.current !== null) window.clearInterval(timerRef.current);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [cargar]);

  const alertas: ComplianceAlertDTO[] = data?.alerts ?? [];
  const hayAlertas = alertas.length > 0;
  // `protocols_evaluated === 0` con 0 alertas NO es un "todo bien": es que no
  // había predicción contra la cual evaluar las reglas. Sin esta distinción el
  // panel mostraba un semáforo verde mientras el Context Engine no publicaba
  // nada, que es la peor falla posible en un panel de monitoreo.
  const sinDatosParaEvaluar = data !== null && data.protocols_evaluated === 0;

  return (
    <Card variant="standard">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h2 className="font-bold text-slate-800">Cumplimiento de protocolos</h2>
          <p className="text-xs text-slate-500 mt-1">
            Se actualiza cada 30 segundos. Una alerta aparece cuando la regla se
            cumple y la zona no tiene una observación reciente.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {hayAlertas && (
            <Badge variant="error">
              {alertas.length} {alertas.length === 1 ? 'alerta' : 'alertas'}
            </Badge>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void cargar()}
            disabled={isLoading}
            aria-label="Actualizar cumplimiento"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-3 mb-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {isLoading && !data && (
        <p className="text-sm text-slate-400 italic">Evaluando cumplimiento…</p>
      )}

      {!isLoading && !error && sinDatosParaEvaluar && (
        <div className="p-3 mb-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
          <p className="font-medium">No hay datos de predicción disponibles</p>
          <p className="mt-1 text-amber-700">
            No hay datos de predicción disponibles para evaluar las reglas en este
            momento. Ningún protocolo se evaluó, así que no se puede afirmar que
            estén cumpliendo.
          </p>
        </div>
      )}

      {!isLoading && !error && !hayAlertas && !sinDatosParaEvaluar && (
        <p className="text-sm text-slate-400 italic">
          Sin incumplimientos: {data?.protocols_evaluated ?? 0}{' '}
          {data?.protocols_evaluated === 1 ? 'regla se está' : 'reglas se están'}
          cumpliendo con su observación al día.
        </p>
      )}

      {hayAlertas && (
        <ul className="space-y-3">
          {alertas.map((alerta, index) => (
            <li
              key={`${alerta.protocol_id}-${alerta.zone_id ?? 'sin-zona'}-${index}`}
              className={`p-3 rounded-lg border ${
                alerta.severity === 'critical'
                  ? 'bg-red-50 border-red-200'
                  : 'bg-amber-50 border-amber-200'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-800 truncate">
                    {alerta.protocol_name}
                    {alerta.zone_name ? ` · ${alerta.zone_name}` : ''}
                  </p>
                  <p className="text-xs text-slate-600 mt-1">{alerta.detail}</p>
                </div>
                <Badge
                  variant={alerta.severity === 'critical' ? 'error' : 'warning'}
                  className="shrink-0"
                >
                  {alerta.severity === 'critical' ? (
                    <AlertTriangle className="w-3 h-3 mr-1" />
                  ) : (
                    <Clock className="w-3 h-3 mr-1" />
                  )}
                  {alerta.overdue_minutes} min
                </Badge>
              </div>
              <dl className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                <div>
                  <dt className="text-slate-500">Métrica</dt>
                  <dd className="text-slate-800">
                    {METRIC_LABELS[alerta.trigger_metric] ?? alerta.trigger_metric}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Valor actual</dt>
                  <dd className="text-slate-800 font-medium">
                    {formatMetricValue(alerta.trigger_metric, alerta.current_value)}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Umbral</dt>
                  <dd className="text-slate-800">
                    {formatMetricValue(alerta.trigger_metric, alerta.threshold_value)}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Última observación</dt>
                  <dd className="text-slate-800">
                    {alerta.minutes_since_last_observation === null
                      ? 'nunca'
                      : `hace ${alerta.minutes_since_last_observation} min`}
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}

      {data && (
        <p className="text-xs text-slate-400 mt-3">
          Evaluado {new Date(data.evaluated_at).toLocaleTimeString('es-AR')} ·{' '}
          {data.protocols_evaluated}{' '}
          {data.protocols_evaluated === 1
            ? 'protocolo evaluado'
            : 'protocolos evaluados'}
        </p>
      )}
    </Card>
  );
}