import { useMemo } from 'react';
import { ClipboardList } from 'lucide-react';
import { useEventReport } from '../../../../hooks/useEventReports';
import { endpoints } from '../../../../core/api/endpoints';
import type { FieldCensusDTO } from '../../types';
import { ReportSection } from './ReportSection';
import { MetricMini } from './MetricMini';
import { DEFAULT_TIMEZONE, formatLocalDateTime, percentage, serviceLabel } from './reportFormat';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export interface ReportFieldCensusSectionProps {
  start?: string;
  end?: string;
}

/** Verde < 80%, amarillo 80-100%, rojo > 100% (saturación de la zona). */
function occupancyTone(percent: number): string {
  if (percent > 100) return 'bg-red-100 text-red-800 border-red-200';
  if (percent >= 80) return 'bg-amber-100 text-amber-800 border-amber-200';
  return 'bg-emerald-100 text-emerald-800 border-emerald-200';
}

export function ReportFieldCensusSection({
  start,
  end,
}: ReportFieldCensusSectionProps = {}) {
  const params = useMemo(() => ({ start, end }), [start, end]);

  const { data, isLoading, error, refresh } = useEventReport<FieldCensusDTO>(
    EVENT_ID,
    endpoints.reports.fieldCensus(EVENT_ID),
    { params }
  );

  const zones = data?.zones ?? [];
  const withObservations = zones.reduce((sum, zone) => sum + zone.observations_count, 0);
  const withoutCapacity = zones.filter(
    (zone) => zone.occupancy_percent === null
  ).length;
  const overCapacity = zones.filter(
    (zone) => (zone.occupancy_percent ?? 0) > 100
  ).length;

  return (
    <ReportSection
      title="Censo Operativo"
      subtitle="densidad observada en campo por zona"
      loading={isLoading}
      error={error}
      hasData={!!data}
      emptyText="Aún no hay observaciones de campo registradas para este período."
      onRefresh={() => void refresh()}
    >
      {zones.length > 0 && (
        <MetricMini
          icon={ClipboardList}
          label="Observaciones de campo"
          value={withObservations}
          sub={`${zones.length} zonas relevadas`}
          accent="text-teal-600"
          iconBg="bg-teal-50 border-teal-100"
        />
      )}

      {zones.length > 0 && (
        <>
          <p className="mt-3 text-xs text-slate-500">
            Conteos manuales registrados por un operador sobre el terreno. Reflejan lo que
            ese observador vio, no un sensor.
          </p>
          {withoutCapacity > 0 && (
            <p className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              {withoutCapacity} {withoutCapacity === 1 ? 'zona no tiene' : 'zonas no tienen'}{' '}
              capacidad declarada, por eso no muestran porcentaje de ocupación.
            </p>
          )}
        </>
      )}

      {zones.length > 0 && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="px-3 py-2 font-medium">Zona</th>
                <th className="px-3 py-2 font-medium">Tipo</th>
                <th className="px-3 py-2 font-medium text-right">Observaciones</th>
                <th className="px-3 py-2 font-medium text-right">Densidad Promedio</th>
                <th className="px-3 py-2 font-medium text-right">Densidad Máxima</th>
                <th className="px-3 py-2 font-medium text-right">Ocupación %</th>
                <th className="px-3 py-2 font-medium">Última observación</th>
              </tr>
            </thead>
            <tbody>
              {zones.map((zone) => (
                <tr key={zone.zone_id} className="border-b border-slate-100">
                  <td className="px-3 py-2 text-slate-700">{zone.zone_name}</td>
                  <td className="px-3 py-2 text-slate-600">
                    {zone.zone_type || serviceLabel(zone.zone_type)}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-700">
                    {zone.observations_count}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-700">
                    {zone.observed_density_avg !== null
                      ? zone.observed_density_avg.toFixed(1)
                      : '—'}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-700">
                    {zone.observed_density_max !== null ? zone.observed_density_max : '—'}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {zone.occupancy_percent !== null ? (
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded font-semibold border ${
                          occupancyTone(zone.occupancy_percent)
                        }`}
                        title={
                          zone.capacity && zone.capacity > 0
                            ? `Densidad promedio sobre capacidad ${zone.capacity}`
                            : undefined
                        }
                      >
                        {percentage(zone.occupancy_percent / 100)}
                      </span>
                    ) : (
                      <span
                        className="text-slate-400"
                        title="Capacidad no declarada: no se puede calcular el porcentaje"
                      >
                        sin capacidad
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-500">
                    {zone.last_observed_at
                      ? formatLocalDateTime(zone.last_observed_at, DEFAULT_TIMEZONE)
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {zones.length > 0 && overCapacity > 0 && (
        <p className="mt-2 text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {overCapacity} {overCapacity === 1 ? 'zona superó' : 'zonas superaron'} su capacidad
          declarada en alguna observación.
        </p>
      )}
    </ReportSection>
  );
}
