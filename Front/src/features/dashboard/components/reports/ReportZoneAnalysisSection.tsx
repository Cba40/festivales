import { useMemo, useState } from 'react';
import { MapPinned } from 'lucide-react';
import { useEventReport } from '../../../../hooks/useEventReports';
import { endpoints } from '../../../../core/api/endpoints';
import type { ZoneAnalysisDTO } from '../../types';
import { ReportSection } from './ReportSection';
import { MetricMini } from './MetricMini';
import { serviceLabel } from './reportFormat';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

const CATEGORIES = [
  'parking',
  'bathroom',
  'gastronomy',
  'transport',
  'exit',
  'accommodation',
  'hydration',
  'rest',
  'cajeros',
] as const;

export interface ReportZoneAnalysisSectionProps {
  start?: string;
  end?: string;
}

export function ReportZoneAnalysisSection({
  start,
  end,
}: ReportZoneAnalysisSectionProps = {}) {
  const [category, setCategory] = useState('');

  const params = useMemo(
    () => ({
      start,
      end,
      ...(category ? { service_category: category } : {}),
    }),
    [start, end, category]
  );

  const { data, isLoading, error, refresh } = useEventReport<ZoneAnalysisDTO>(
    EVENT_ID,
    endpoints.reports.zoneAnalysis(EVENT_ID),
    { params }
  );

  const zones = data?.zones ?? [];
  const withDemand = zones.filter((zone) => zone.real_choices > 0).length;
  const totalChoices = zones.reduce((sum, zone) => sum + zone.real_choices, 0);
  const hasDemand = totalChoices > 0;

  return (
    <ReportSection
      title="Análisis de Zonas"
      subtitle="demanda real del usuario y cobertura del sistema por zona"
      loading={isLoading}
      error={error}
      hasData={!!data}
      emptyText={
        data?.zones.length === 0
          ? 'No hay zonas registradas para el filtro seleccionado.'
          : 'Sin datos de zonas.'
      }
      onRefresh={() => void refresh()}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <label className="sr-only" htmlFor="zone-analysis-category">
            Servicio
          </label>
          <select
            id="zone-analysis-category"
            className="px-2 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">Todos los servicios</option>
            {CATEGORIES.map((item) => (
              <option key={item} value={item}>
                {serviceLabel(item)}
              </option>
            ))}
          </select>
        </div>
        {hasDemand && (
          <span className="text-xs text-slate-500">
            {withDemand} de {zones.length} zonas con elecciones registradas
          </span>
        )}
      </div>

      {zones.length > 0 && (
        <MetricMini
          icon={MapPinned}
          label="Elecciones de zona"
          value={totalChoices}
          sub="clics del usuario en una zona concreta"
          accent="text-emerald-600"
          iconBg="bg-emerald-50 border-emerald-100"
        />
      )}

      {zones.length > 0 && !hasDemand && (
        <p className="mt-3 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          Aún no hay registros de selección de zona para este servicio. El sistema solo
          muestra las veces que fue recomendada.
        </p>
      )}

      {zones.length > 0 && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="px-3 py-2 font-medium">Zona</th>
                <th className="px-3 py-2 font-medium">Tipo</th>
                <th className="px-3 py-2 font-medium text-right">Elecciones Reales</th>
                <th className="px-3 py-2 font-medium text-right">Veces Recomendada</th>
                <th className="px-3 py-2 font-medium text-right">Posición Promedio</th>
              </tr>
            </thead>
            <tbody>
              {zones.map((zone) => (
                <tr key={zone.zone_id} className="border-b border-slate-100">
                  <td className="px-3 py-2 text-slate-700">{zone.zone_name}</td>
                  <td className="px-3 py-2 text-slate-600">{zone.zone_type}</td>
                  <td className="px-3 py-2 text-right">
                    {zone.real_choices > 0 ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                        {zone.real_choices}
                      </span>
                    ) : (
                      <span className="text-slate-300">0</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-700">
                    {zone.recommendation_count}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-600">
                    {zone.avg_position !== null ? zone.avg_position.toFixed(1) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {zones.length > 0 && (
        <p className="mt-2 text-[11px] text-slate-400">
          La posición promedio es el lugar que ocupa la zona en la lista de recomendadas
          (1 = primera). Solo hay datos de elecciones reales en los módulos que registran
          el clic en la zona.
        </p>
      )}
    </ReportSection>
  );
}
