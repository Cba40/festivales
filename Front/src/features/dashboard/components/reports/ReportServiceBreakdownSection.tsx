import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, Layers } from 'lucide-react';
import { useEventReport } from '../../../../hooks/useEventReports';
import { apiClient } from '../../../../core/api/client';
import { endpoints } from '../../../../core/api/endpoints';
import type { ServiceBreakdownDTO } from '../../types';
import { MetricMini } from './MetricMini';
import { ReportSection } from './ReportSection';
import { buildFilterGroups, serviceLabel } from './reportFormat';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

interface ProtocolOption {
  id: string;
  title: string;
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
    </ReportSection>
  );
}