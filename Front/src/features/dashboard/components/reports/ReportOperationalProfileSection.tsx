import { useMemo } from 'react';
import { useEventReport } from '../../../../hooks/useEventReports';
import { endpoints } from '../../../../core/api/endpoints';
import type { OperationalProfileDTO } from '../../types';
import { ReportSection } from './ReportSection';
import {
  phaseDisplayName,
  humanize,
  formatISODate,
  percentage,
} from './reportFormat';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export interface ReportOperationalProfileSectionProps {
  start?: string;
  end?: string;
}

export function ReportOperationalProfileSection({
  start,
  end,
}: ReportOperationalProfileSectionProps = {}) {
  const params = useMemo(() => ({ start, end }), [start, end]);

  const { data, isLoading, error, refresh } = useEventReport<OperationalProfileDTO>(
    EVENT_ID,
    endpoints.reports.operationalProfile(EVENT_ID),
    { params }
  );

  const phases = data?.phases ?? [];

  return (
    <ReportSection
      title="Perfil Operacional"
      subtitle="resumen del flujo operativo del evento"
      loading={isLoading}
      error={error}
      hasData={!!data}
      emptyText={phases.length === 0 ? 'Sin fases operativas registradas.' : 'Sin perfil operativo disponible.'}
      onRefresh={() => void refresh()}
    >
      {data && phases.length > 0 && (
        <div className="space-y-6">
          {phases.map((phase) => {
            const platform = data.platform_queries.find((p) => p.phase_id === phase.phase_id);
            const predictions = data.predictions_summary.find((p) => p.phase_id === phase.phase_id);
            const observations = data.observations_summary.find((p) => p.phase_id === phase.phase_id);
            const operational = data.operational_events_summary.find((p) => p.phase_id === phase.phase_id);

            return (
              <div key={phase.phase_id ?? phase.phase_name} className="border border-slate-200 rounded-lg overflow-hidden">
                <div className="bg-slate-50 px-4 py-3 border-b border-slate-200">
                  <h3 className="font-bold text-slate-800">{phaseDisplayName(phase.phase_name)}</h3>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4">
                  {/* Platform queries */}
                  <section>
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Actividad</h4>
                    {platform ? (
                      <div className="grid grid-cols-2 gap-3">
                        <div className="p-3 bg-slate-50 rounded-lg">
                          <div className="text-lg font-bold text-slate-800">{platform.consultas_total}</div>
                          <div className="text-xs text-slate-500">totales</div>
                        </div>
                        <div className="p-3 bg-slate-50 rounded-lg">
                          <div className="text-lg font-bold text-emerald-700">{platform.with_results}</div>
                          <div className="text-xs text-slate-500">con resultados</div>
                        </div>
                        <div className="p-3 bg-slate-50 rounded-lg">
                          <div className="text-lg font-bold text-amber-700">{platform.empty}</div>
                          <div className="text-xs text-slate-500">brechas de información</div>
                        </div>
                        <div className="p-3 bg-slate-50 rounded-lg">
                          <div className="text-lg font-bold text-slate-600">{platform.unavailable}</div>
                          <div className="text-xs text-slate-500">no disponible</div>
                        </div>
                        <div className="p-3 bg-slate-50 rounded-lg col-span-2">
                          <div className="text-lg font-bold text-red-700">{platform.error}</div>
                          <div className="text-xs text-slate-500">incidencias técnicas</div>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-400 italic">Sin datos de actividad.</p>
                    )}
                  </section>

                  {/* Predictions */}
                  <section>
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Predicciones</h4>
                    {predictions ? (
                      <div>
                        <div className="text-lg font-bold text-slate-800">{predictions.predictions_count} predicciones</div>
                        <ul className="mt-2 space-y-1">
                          {predictions.zones.map((z) => (
                            <li key={z.zone_id ?? z.zone_name} className="flex justify-between text-sm">
                              <span className="text-slate-700">{z.zone_name}</span>
                              <span className="text-slate-500">
                                {z.projected_density !== null ? `${z.projected_density}` : 'N/A'}
                                {z.operational_state ? ` · ${humanize(z.operational_state)}` : ''}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-400 italic">Sin datos de predicciones.</p>
                    )}
                  </section>

                  {/* Observations */}
                  <section>
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Observaciones</h4>
                    {observations ? (
                      <div>
                        <div className="text-lg font-bold text-slate-800">{observations.observations_count} observaciones</div>
                        <ul className="mt-2 space-y-1">
                          {observations.zones.map((z) => (
                            <li key={z.zone_id} className="flex justify-between text-sm">
                              <span className="text-slate-700">{z.zone_name}</span>
                              <span className="text-slate-500">
                                {z.observations_count} ({percentage(z.observations_count)}), densidad {z.observed_density_total} total / {z.observed_density_avg !== null ? z.observed_density_avg.toFixed(1) : 'N/A'} avg
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-400 italic">Sin datos de observaciones.</p>
                    )}
                  </section>

                  {/* Operational events */}
                  <section>
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Eventos operativos</h4>
                    {operational ? (
                      <div>
                        <div className="text-lg font-bold text-slate-800">
                          {operational.total_events} eventos · {operational.incidents} incidentes
                        </div>
                        <ul className="mt-2 space-y-1">
                          {operational.events.map((ev) => (
                            <li key={ev.operational_event_id} className="text-sm">
                              <span className="text-slate-700">{humanize(ev.event_type)}</span>
                              {ev.is_incident && (
                                <span className="ml-1 text-[10px] font-medium text-red-700 bg-red-50 border border-red-200 rounded px-1.5 py-0.5">
                                  Incidente
                                </span>
                              )}
                              <div className="text-xs text-slate-500">
                                {formatISODate(ev.start_timestamp)} - {formatISODate(ev.end_timestamp)}
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-400 italic">Sin datos de eventos operativos.</p>
                    )}
                  </section>
                </div>
              </div>
            );
          })}

          {data.insufficient_data.length > 0 && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700">
              <div className="font-medium mb-1">Advertencias de datos</div>
              <ul className="list-disc pl-5 space-y-1">
                {data.insufficient_data.map((note, i) => (
                  <li key={i}>{note}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </ReportSection>
  );
}