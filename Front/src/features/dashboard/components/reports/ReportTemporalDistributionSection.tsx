import { useEventReport } from '../../../../hooks/useEventReports';
import { endpoints } from '../../../../core/api/endpoints';
import type { TemporalDistributionDTO } from '../../types';
import { ReportSection } from './ReportSection';
import { formatLocalBucket, humanize, DEFAULT_TIMEZONE } from './reportFormat';
import { useState, useMemo } from 'react';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export interface ReportTemporalDistributionSectionProps {
  start?: string;
  end?: string;
}

export function ReportTemporalDistributionSection({
  start,
  end,
}: ReportTemporalDistributionSectionProps = {}) {
  const [granularity, setGranularity] = useState<'hour' | 'day'>('hour');

  const params = useMemo(
    () => ({ granularity, timezone: DEFAULT_TIMEZONE, start, end }),
    [granularity, start, end]
  );

  const { data, isLoading, error, refresh } = useEventReport<TemporalDistributionDTO>(
    EVENT_ID,
    endpoints.reports.temporalDistribution(EVENT_ID),
    { params }
  );

  return (
    <ReportSection
      title="Distribución Temporal"
      subtitle="actividad registrada por intervalo"
      loading={isLoading}
      error={error}
      hasData={!!data}
      emptyText="Sin datos de distribución temporal."
      onRefresh={() => void refresh()}
    >
      {data && (
        <div className="space-y-4">
          <div className="print:hidden flex items-center justify-between">
            <div>
              <span className="text-sm font-medium text-slate-700">
                Granularidad:{" "}
              </span>
              <select
                value={granularity}
                onChange={(e) => setGranularity(e.target.value as 'hour' | 'day')}
                className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="hour">Por hora</option>
                <option value="day">Por día</option>
              </select>
            </div>
            <span className="text-xs text-slate-500">
              TZ: {DEFAULT_TIMEZONE}
            </span>
          </div>

          {data.buckets.length === 0 && (
            <p className="text-sm text-slate-500 text-center">
              No hay actividad registrada para la granularidad seleccionada.
            </p>
          )}

          {data.buckets.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-slate-200">
                    <th className="px-5 py-2 font-medium">Intervalo</th>
                    <th className="px-5 py-2 font-medium">Actividad</th>
                    {granularity === 'hour' && (
                      <th className="px-5 py-2 font-medium">Fase</th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {data.buckets.map((bucket) => (
                    <tr key={bucket.bucket} className="border-b border-slate-100">
                      <td className="px-5 py-2 text-slate-600">
                        {formatLocalBucket(bucket.bucket)}
                      </td>
                      <td className="px-5 py-2 text-slate-700">{bucket.count}</td>
                      {granularity === 'hour' && bucket.phase && (
                        <td className="px-5 py-2">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                              bucket.phase === 'unassigned'
                                ? 'bg-slate-100 text-slate-700 border-slate-200'
                                : 'bg-indigo-100 text-indigo-800 border-indigo-200'
                            }`}
                          >
                            {bucket.phase === 'unassigned'
                              ? 'Sin fase'
                              : humanize(bucket.phase)}
                          </span>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </ReportSection>
  );
}