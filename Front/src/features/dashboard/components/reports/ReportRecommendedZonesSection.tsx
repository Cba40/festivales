import { useEventReport } from '../../../../hooks/useEventReports';
import { endpoints } from '../../../../core/api/endpoints';
import type { RecommendedZonesDTO } from '../../types';
import { ReportSection } from './ReportSection';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function ReportRecommendedZonesSection() {
  const { data, isLoading, error, refresh } = useEventReport<RecommendedZonesDTO>(
    EVENT_ID,
    endpoints.reports.recommendedZones(EVENT_ID)
  );

  return (
    <ReportSection
      title="Zonas Recomendadas"
      subtitle="zonas por cantidad de recomendaciones"
      loading={isLoading}
      error={error}
      hasData={!!data}
      emptyText={data?.zones.length === 0 ? 'No hay zonas recomendadas.' : 'Sin recomendaciones registradas.'}
      onRefresh={() => void refresh()}
    >
      {data && data.zones.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="px-5 py-2 font-medium">Zona</th>
                <th className="px-5 py-2 font-medium">Tipo</th>
                <th className="px-5 py-2 font-medium">Recomendaciones</th>
              </tr>
            </thead>
            <tbody>
              {data.zones.map((zone) => (
                <tr key={zone.zone_id} className="border-b border-slate-100">
                  <td className="px-5 py-2 text-slate-700">{zone.zone_name}</td>
                  <td className="px-5 py-2 text-slate-600">{zone.zone_type}</td>
                  <td className="px-5 py-2 text-slate-700">{zone.recommendations}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ReportSection>
  );
}