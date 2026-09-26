import { useMemo, useState } from 'react';
import { useEventReport } from '../../../../hooks/useEventReports';
import { endpoints } from '../../../../core/api/endpoints';
import type { CoverageGapsDTO } from '../../types';
import { ReportSection } from './ReportSection';
import { formatDateOnly, percentage, serviceLabel, DEFAULT_TIMEZONE } from './reportFormat';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export interface ReportCoverageGapsSectionProps {
  start?: string;
  end?: string;
}

export function ReportCoverageGapsSection({
  start,
  end,
}: ReportCoverageGapsSectionProps = {}) {
  const [originFilter, setOriginFilter] = useState('');

  const params = useMemo(
    () => ({ start, end, ...(originFilter ? { origin: originFilter } : {}) }),
    [start, end, originFilter]
  );

  const { data, isLoading, error, refresh } = useEventReport<CoverageGapsDTO>(
    EVENT_ID,
    endpoints.reports.coverageGaps(EVENT_ID),
    { params }
  );

  return (
    <ReportSection
      title="Cobertura de Datos por Servicio"
      subtitle="requests técnicos que volvieron sin resultados"
      loading={isLoading}
      error={error}
      hasData={!!data}
      emptyText="Todos los requests técnicos devolvieron resultados."
      onRefresh={() => void refresh()}
    >
      {data && (
        <div className="space-y-6">
          <div className="print:hidden flex flex-wrap items-end justify-between gap-3">
            <div>
              <label
                className="block text-sm font-medium text-slate-700 mb-1"
                htmlFor="coverage-origin"
              >
                Origen de requests
              </label>
              <select
                id="coverage-origin"
                className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                value={originFilter}
                onChange={(e) => setOriginFilter(e.target.value)}
              >
                <option value="">Todos (incluye automático)</option>
                <option value="user">Solo usuario (intención real)</option>
                <option value="prefetch">Solo prefetch</option>
                <option value="system">Solo sistema (polling, SWR)</option>
              </select>
            </div>
            <span className="text-xs text-slate-500">TZ: {DEFAULT_TIMEZONE}</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b border-slate-200">
                  <th className="px-5 py-2 font-medium">Servicio</th>
                  <th className="px-5 py-2 font-medium">Requests técnicos</th>
                  <th className="px-5 py-2 font-medium">Requests sin resultados</th>
                  <th className="px-5 py-2 font-medium">Tasa de brecha</th>
                </tr>
              </thead>
              <tbody>
                {data.services.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-5 py-8 text-center text-slate-400 italic">
                      Sin servicios con requests sin resultados.
                    </td>
                  </tr>
                )}
                {data.services.map((service) => (
                  <tr key={service.service_category} className="border-b border-slate-100">
                    <td className="px-5 py-2 text-slate-700">
                      {serviceLabel(service.service_category)}
                    </td>
                    <td className="px-5 py-2 text-slate-700">{service.total_consultas}</td>
                    <td className="px-5 py-2 text-slate-700">{service.empty_count}</td>
                    <td className="px-5 py-2 text-amber-700">{percentage(service.empty_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.temporal_distribution.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">
                Requests sin resultados por día
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-slate-500 border-b border-slate-200">
                      <th className="px-5 py-2 font-medium">Día</th>
                      <th className="px-5 py-2 font-medium">Requests sin resultados</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.temporal_distribution.map((bucket) => (
                      <tr key={bucket.day} className="border-b border-slate-100">
                        <td className="px-5 py-2 text-slate-600">{formatDateOnly(bucket.day)}</td>
                        <td className="px-5 py-2 text-slate-700">{bucket.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </ReportSection>
  );
}