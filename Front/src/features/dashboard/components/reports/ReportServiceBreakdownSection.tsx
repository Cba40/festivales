import { Layers } from 'lucide-react';
import { useEventReport } from '../../../../hooks/useEventReports';
import { endpoints } from '../../../../core/api/endpoints';
import type { ServiceBreakdownDTO } from '../../types';
import { MetricMini } from './MetricMini';
import { ReportSection } from './ReportSection';
import { serviceLabel } from './reportFormat';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function ReportServiceBreakdownSection() {
  const { data, isLoading, error, refresh } = useEventReport<ServiceBreakdownDTO>(
    EVENT_ID,
    endpoints.reports.serviceBreakdown(EVENT_ID)
  );
  const total = data?.services.reduce((sum, service) => sum + service.total_consultas, 0) ?? 0;

  return (
    <ReportSection
      title="Actividad por Servicio"
      subtitle="distribución de interacciones digitales"
      loading={isLoading}
      error={error}
      hasData={!!data}
      emptyText="Sin actividad registrada para el evento."
      onRefresh={() => void refresh()}
    >
      {data && data.services.length > 0 && (
        <MetricMini
          icon={Layers}
          label="Categorías de servicio"
          value={data.services.length}
          sub={`${total} actividades en total`}
          accent="text-indigo-600"
          iconBg="bg-indigo-50 border-indigo-100"
        />
      )}
      {data && (
        <div className="mt-4 space-y-3">
          {data.services.map((service) => (
            <div key={service.service_category} className="flex items-center gap-3">
              <div className="w-40 shrink-0 text-sm text-slate-700">
                {serviceLabel(service.service_category)}
              </div>
              <div className="flex-1">
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 rounded-full"
                    style={{ width: `${Math.min(service.percentage, 100)}%` }}
                  />
                </div>
              </div>
              <div className="w-24 shrink-0 text-right text-sm text-slate-600">
                {service.total_consultas} ({service.percentage.toFixed(1)}%)
              </div>
            </div>
          ))}
        </div>
      )}
    </ReportSection>
  );
}