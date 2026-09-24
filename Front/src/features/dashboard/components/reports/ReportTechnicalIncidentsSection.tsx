import { useEventReport } from '../../../../hooks/useEventReports';
import { endpoints } from '../../../../core/api/endpoints';
import type { TechnicalIncidentsDTO } from '../../types';
import { ReportSection } from './ReportSection';
import { formatDateOnly, percentage, serviceLabel } from './reportFormat';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function ReportTechnicalIncidentsSection() {
  const { data, isLoading, error, refresh } = useEventReport<TechnicalIncidentsDTO>(
    EVENT_ID,
    endpoints.reports.technicalIncidents(EVENT_ID)
  );

  return (
    <ReportSection
      title="Incidencias Técnicas"
      subtitle="consultas con error en el servicio"
      loading={isLoading}
      error={error}
      hasData={!!data}
      emptyText="Sin incidencias técnicas registradas."
      onRefresh={() => void refresh()}
    >
      {data && (
        <div className="space-y-6">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b border-slate-200">
                  <th className="px-5 py-2 font-medium">Servicio</th>
                  <th className="px-5 py-2 font-medium">Con error</th>
                  <th className="px-5 py-2 font-medium">Tasa de incidencia</th>
                </tr>
              </thead>
              <tbody>
                {data.services.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-5 py-8 text-center text-slate-400 italic">
                      Sin incidencias técnicas.
                    </td>
                  </tr>
                )}
                {data.services.map((service) => (
                  <tr key={service.service_category} className="border-b border-slate-100">
                    <td className="px-5 py-2 text-slate-700">
                      {serviceLabel(service.service_category)}
                    </td>
                    <td className="px-5 py-2 text-slate-700">{service.error_count}</td>
                    <td className="px-5 py-2 text-red-700">{percentage(service.error_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.temporal_distribution.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">
                Distribución temporal de incidencias
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-slate-500 border-b border-slate-200">
                      <th className="px-5 py-2 font-medium">Día</th>
                      <th className="px-5 py-2 font-medium">Incidencias</th>
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