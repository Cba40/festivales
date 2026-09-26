import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, Layers, BarChart3 } from 'lucide-react';
import { useEventReport } from '../../../../hooks/useEventReports';
import { apiClient } from '../../../../core/api/client';
import { endpoints } from '../../../../core/api/endpoints';
import type { ServiceBreakdownDTO, TemporalDistributionDTO } from '../../types';
import { MetricMini } from './MetricMini';
import { ReportSection } from './ReportSection';
import {
  buildFilterGroups,
  DEFAULT_TIMEZONE,
  formatLocalBucket,
  humanize,
  serviceLabel,
} from './reportFormat';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

interface ProtocolOption {
  id: string;
  title: string;
}

interface TemporalBreakdownProps {
  start?: string;
  end?: string;
  categories: string[];
}

// Sub-bloque "cuándo" que acompaña al desglose "cuántas". Comparte período con
// la sección padre y reutiliza los mismos request_mode del desglose por filtro:
// el operador copia el prefijo crudo del acordeón y obtiene su curva horaria.
function TemporalBreakdown({ start, end, categories }: TemporalBreakdownProps) {
  const [prefix, setPrefix] = useState('');
  const [category, setCategory] = useState('');

  const params = useMemo(
    () => ({
      start,
      end,
      granularity: 'hour' as const,
      timezone: DEFAULT_TIMEZONE,
      ...(prefix ? { request_mode_prefix: prefix } : {}),
      ...(category ? { service_category: category } : {}),
    }),
    [start, end, prefix, category]
  );

  const { data, isLoading, error } = useEventReport<TemporalDistributionDTO>(
    EVENT_ID,
    endpoints.reports.temporalDistribution(EVENT_ID),
    { params }
  );

  const buckets = data?.buckets ?? [];
  const total = buckets.reduce((sum, bucket) => sum + bucket.count, 0);
  const title = category
    ? `¿Cuándo buscaron ${serviceLabel(category).toLowerCase()}?`
    : '¿Cuándo se consultaron los servicios?';

  return (
    <div className="mt-4 border-t border-slate-200 pt-3">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          <BarChart3 size={14} className="text-indigo-500" />
          {title}
        </h4>
        <div className="flex flex-wrap items-center gap-2">
          <label className="sr-only" htmlFor="breakdown-timeline-category">
            Servicio
          </label>
          <select
            id="breakdown-timeline-category"
            className="px-2 py-1 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">Todos los servicios</option>
            {categories.map((item) => (
              <option key={item} value={item}>
                {serviceLabel(item)}
              </option>
            ))}
          </select>
          <label className="sr-only" htmlFor="breakdown-timeline-prefix">
            Filtro aplicado
          </label>
          <input
            id="breakdown-timeline-prefix"
            className="px-2 py-1 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 w-40"
            placeholder="salida_vehicular="
            title="Prefijo de request_mode (copialo del desglose por filtro)"
            value={prefix}
            onChange={(e) => setPrefix(e.target.value)}
          />
        </div>
      </div>

      {error && (
        <p className="text-xs text-red-600">No se pudo cargar la distribución horaria.</p>
      )}

      {!error && isLoading && buckets.length === 0 && (
        <p className="text-xs text-slate-500">Calculando distribución horaria…</p>
      )}

      {!error && !isLoading && buckets.length === 0 && (
        <p className="text-xs text-slate-500">
          Sin actividad registrada para el filtro y la categoría seleccionados.
        </p>
      )}

      {buckets.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="px-3 py-1.5 font-medium">Intervalo</th>
                <th className="px-3 py-1.5 font-medium">Actividad</th>
                <th className="px-3 py-1.5 font-medium">Fase</th>
              </tr>
            </thead>
            <tbody>
              {buckets.map((bucket) => (
                <tr key={bucket.bucket} className="border-b border-slate-100">
                  <td className="px-3 py-1.5 text-slate-600">{formatLocalBucket(bucket.bucket)}</td>
                  <td className="px-3 py-1.5 font-medium text-slate-700">{bucket.count}</td>
                  <td className="px-3 py-1.5">
                    {bucket.phase ? (
                      <span
                        className={`inline-flex items-center px-1.5 py-0.5 rounded font-medium ${
                          bucket.phase === 'unassigned'
                            ? 'bg-slate-100 text-slate-700 border-slate-200'
                            : 'bg-indigo-100 text-indigo-800 border-indigo-200'
                        }`}
                      >
                        {bucket.phase === 'unassigned' ? 'Sin fase' : humanize(bucket.phase)}
                      </span>
                    ) : (
                      <span className="text-slate-300">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="text-slate-600">
                <td className="px-3 py-1.5 font-medium">Total</td>
                <td className="px-3 py-1.5 font-semibold text-slate-800">{total}</td>
                <td />
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {buckets.length > 0 && (
        <p className="mt-1.5 text-[11px] text-slate-400">
          Zona horaria {DEFAULT_TIMEZONE}. El filtro acepta el prefijo crudo del desglose
          (ej.: <span className="font-mono">salida_vehicular=</span>).
        </p>
      )}
    </div>
  );
}

export interface ReportServiceBreakdownSectionProps {
  start?: string;
  end?: string;
}

export function ReportServiceBreakdownSection({
  start,
  end,
}: ReportServiceBreakdownSectionProps = {}) {
  const params = useMemo(() => ({ start, end }), [start, end]);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [protocolTitles, setProtocolTitles] = useState<Record<string, string>>({});

  const { data, isLoading, error, refresh } = useEventReport<ServiceBreakdownDTO>(
    EVENT_ID,
    endpoints.reports.serviceBreakdown(EVENT_ID),
    { params }
  );

  // Los request_mode de protocolo llegan como id opaco: el catálogo público
  // permite mostrarlos con su título real ("Niño perdido", "Persona herida").
  useEffect(() => {
    let cancelled = false;
    apiClient
      .get<ProtocolOption[]>(endpoints.emergency.protocols('festival'))
      .then(({ data: list }) => {
        if (cancelled) return;
        const titles: Record<string, string> = {};
        for (const protocol of list ?? []) titles[protocol.id] = protocol.title;
        setProtocolTitles(titles);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const total = data?.services.reduce((sum, service) => sum + service.total_consultas, 0) ?? 0;
  const filterGroups = useMemo(
    () => buildFilterGroups(data?.services ?? [], data?.filters, protocolTitles),
    [data, protocolTitles]
  );

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
      {data && filterGroups.length > 0 && (
        <div className="mt-5 border-t border-slate-200 pt-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
            Desglose por filtro aplicado
          </h4>
          <ul className="divide-y divide-slate-100">
            {filterGroups.map((group) => {
              const expandable = group.children.length > 0;
              const open = Boolean(expanded[group.key]);
              return (
                <li key={group.key} className="py-1">
                  <button
                    type="button"
                    onClick={() => {
                      if (!expandable) return;
                      setExpanded((prev) => ({ ...prev, [group.key]: !prev[group.key] }));
                    }}
                    className={`w-full flex items-center gap-2 text-left text-sm ${
                      expandable ? 'cursor-pointer hover:text-indigo-700' : 'cursor-default'
                    }`}
                  >
                    {expandable ? (
                      open ? (
                        <ChevronDown size={14} className="shrink-0 text-slate-400" />
                      ) : (
                        <ChevronRight size={14} className="shrink-0 text-slate-400" />
                      )
                    ) : (
                      <span className="w-[14px] shrink-0" />
                    )}
                    <span className="flex-1 text-slate-700">{group.label}</span>
                    <span className="shrink-0 text-xs text-slate-500">Total: {group.total}</span>
                  </button>
                  {expandable && open && (
                    <ul className="mt-1 mb-1 space-y-0.5">
                      {group.children.map((child) => (
                        <li
                          key={child.key}
                          className="flex items-center gap-2 pl-6 text-xs text-slate-600"
                        >
                          <span className="flex-1 truncate" title={`${child.label} (${child.key})`}>
                            {child.label}
                          </span>
                          <span className="shrink-0 text-slate-500">{child.total}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
      {data && data.services.length > 0 && (
        <TemporalBreakdown
          start={start}
          end={end}
          categories={data.services.map((service) => service.service_category)}
        />
      )}
    </ReportSection>
  );
}