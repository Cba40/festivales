import { AlertTriangle, CheckCircle2, Search, WifiOff } from 'lucide-react';
import { useEventReport } from '../../../../hooks/useEventReports';
import { endpoints } from '../../../../core/api/endpoints';
import type { EventSummaryDTO } from '../../types';
import { MetricMini } from './MetricMini';
import { ReportSection } from './ReportSection';
import { RESULT_STATUS_LABELS } from './reportFormat';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function ReportSummarySection() {
  const { data, isLoading, error, refresh } = useEventReport<EventSummaryDTO>(
    EVENT_ID,
    endpoints.reports.summary(EVENT_ID)
  );

  return (
    <ReportSection
      title="Resumen de Consultas"
      subtitle="interacciones digitales del evento"
      loading={isLoading}
      error={error}
      hasData={!!data}
      emptyText="Sin consultas registradas para el evento."
      onRefresh={() => void refresh()}
    >
      {data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <MetricMini
              icon={Search}
              label="Consultas totales"
              value={data.total_consultas}
              accent="text-indigo-600"
              iconBg="bg-indigo-50 border-indigo-100"
            />
            <MetricMini
              icon={CheckCircle2}
              label="Con resultados"
              value={data.with_results}
              accent="text-emerald-600"
              iconBg="bg-emerald-50 border-emerald-100"
            />
            <MetricMini
              icon={AlertTriangle}
              label="Brechas de información"
              value={data.coverage_gaps_empty}
              accent="text-amber-600"
              iconBg="bg-amber-50 border-amber-100"
            />
            <MetricMini
              icon={WifiOff}
              label="Incidencias técnicas"
              value={data.technical_errors}
              accent="text-red-600"
              iconBg="bg-red-50 border-red-100"
            />
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b border-slate-200">
                  <th className="px-5 py-2 font-medium">Resultado</th>
                  <th className="px-5 py-2 font-medium">Consultas</th>
                </tr>
              </thead>
              <tbody>
                {data.breakdown.map((item) => (
                  <tr key={item.result_status} className="border-b border-slate-100">
                    <td className="px-5 py-2 text-slate-700">
                      {RESULT_STATUS_LABELS[item.result_status] ?? item.result_status}
                    </td>
                    <td className="px-5 py-2 text-slate-700">{item.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </ReportSection>
  );
}