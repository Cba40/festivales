import { useState, useEffect, useMemo } from 'react';
import { RotateCcw, Check, X } from 'lucide-react';
import { EVENT_ID } from './constants';
import { useEventDayZoneFactors, useEventStates, useZoneTypes } from '../../hooks/useContextEngine';
import type { EventDayZoneFactorDTO, EventDayZoneFactorCreatePayload } from '../../hooks/useContextEngine';

interface CellValue {
  saturation: number;
  attendance: number;
  resource: number;
  priority: number;
  factorId?: string;
}

interface ZoneFactorMatrixProps {
  eventDayId: string;
  eventId?: string;
}

export function ZoneFactorMatrix({ eventDayId, eventId }: ZoneFactorMatrixProps) {
  const eid = eventId || EVENT_ID;
  const { states: eventStates, loading: statesLoading } = useEventStates(eid);
  const { types: zoneTypes, loading: typesLoading } = useZoneTypes();
  const { factors, loading: factorsLoading, error, fetchFactors, createFactor, updateFactor, deleteFactor } = useEventDayZoneFactors(eid);

  const ztMap = useMemo(() => Object.fromEntries(zoneTypes.map(zt => [zt.slug, zt.id])), [zoneTypes]);
  const esMap = useMemo(() => Object.fromEntries(eventStates.map(es => [es.slug, es.id])), [eventStates]);

  const [cells, setCells] = useState<Record<string, Record<string, CellValue>>>({});
  const [editing, setEditing] = useState<Record<string, boolean>>({});
  const [savingCells, setSavingCells] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (eventDayId) fetchFactors(eventDayId);
  }, [eventDayId, fetchFactors]);

  useEffect(() => {
    if (zoneTypes.length === 0 || eventStates.length === 0) return;
    const next: Record<string, Record<string, CellValue>> = {};
    for (const zt of zoneTypes) {
      next[zt.slug] = {};
      for (const st of eventStates) {
        const factor = factors.find(
          (f: EventDayZoneFactorDTO) =>
            f.zone_type_id === ztMap[zt.slug] && f.event_state_id === esMap[st.slug]
        );
        if (factor) {
          next[zt.slug][st.slug] = {
            saturation: factor.saturation_factor,
            attendance: factor.attendance_factor,
            resource: factor.resource_factor,
            priority: factor.priority_weight,
            factorId: factor.id,
          };
        } else {
          const defs = zt.default_factors?.[st.slug];
          next[zt.slug][st.slug] = {
            saturation: defs?.saturation ?? 1.0,
            attendance: defs?.attendance ?? 1.0,
            resource: defs?.resource ?? 1.0,
            priority: 50,
          };
        }
      }
    }
    setCells(next);
  }, [factors, zoneTypes, eventStates, ztMap, esMap]);

  const cellKey = (zt: string, st: string) => `${zt}|${st}`;

  const handleFieldChange = (zt: string, st: string, field: string, raw: string) => {
    const val = field === 'priority' ? parseInt(raw) || 0 : parseFloat(raw) || 0;
    const clamped = field === 'priority' ? Math.max(0, Math.min(100, val)) : Math.max(0, Math.min(2, val));
    setCells(prev => ({
      ...prev,
      [zt]: { ...prev[zt], [st]: { ...prev[zt][st], [field]: clamped } },
    }));
  };

  const saveCell = async (zt: string, st: string) => {
    const cell = cells[zt]?.[st];
    if (!cell) return;
    const key = cellKey(zt, st);
    setSavingCells(prev => ({ ...prev, [key]: true }));
    try {
      if (cell.factorId) {
        const updated = await updateFactor(cell.factorId, {
          saturation_factor: cell.saturation,
          attendance_factor: cell.attendance,
          resource_factor: cell.resource,
          priority_weight: Math.round(cell.priority),
        });
        if (updated) setEditing(prev => ({ ...prev, [key]: false }));
      } else {
        const payload: EventDayZoneFactorCreatePayload = {
          event_day_id: eventDayId,
          zone_type_id: ztMap[zt],
          event_state_id: esMap[st],
          saturation_factor: cell.saturation,
          attendance_factor: cell.attendance,
          resource_factor: cell.resource,
          priority_weight: Math.round(cell.priority),
        };
        const created = await createFactor(payload);
        if (created) {
          setCells(prev => ({
            ...prev,
            [zt]: { ...prev[zt], [st]: { ...prev[zt][st], factorId: created.id } },
          }));
          setEditing(prev => ({ ...prev, [key]: false }));
        }
      }
    } finally {
      setSavingCells(prev => ({ ...prev, [key]: false }));
    }
  };

  const resetCell = async (zt: string, st: string) => {
    const cell = cells[zt]?.[st];
    if (!cell?.factorId) return;
    await deleteFactor(cell.factorId);
    const ztObj = zoneTypes.find(t => t.slug === zt);
    const defs = ztObj?.default_factors?.[st];
    setCells(prev => ({
      ...prev,
      [zt]: {
        ...prev[zt],
        [st]: {
          saturation: defs?.saturation ?? 1.0,
          attendance: defs?.attendance ?? 1.0,
          resource: defs?.resource ?? 1.0,
          priority: 50,
        },
      },
    }));
  };

  const loading = statesLoading || typesLoading || factorsLoading;

  if (loading) {
    return <div className="text-center py-8 text-slate-500 italic">Cargando factores...</div>;
  }

  if (error) {
    return <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr>
            <th className="px-2 py-1.5 text-left text-slate-500 font-medium border-b border-slate-200 bg-slate-50 sticky left-0 z-10">
              Tipo zona
            </th>
            {eventStates.map(st => (
              <th
                key={st.slug}
                className="px-2 py-1.5 text-center font-medium border-b border-slate-200 bg-slate-50 min-w-[100px]"
                style={{ color: st.color }}
              >
                {st.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {zoneTypes.map(zt => (
            <tr key={zt.slug}>
              <td className="px-2 py-2 text-slate-700 font-medium border-b border-slate-100 sticky left-0 bg-white z-10">
                {zt.name}
              </td>
              {eventStates.map(st => {
                const cell = cells[zt.slug]?.[st.slug];
                const key = cellKey(zt.slug, st.slug);
                const isEditingCell = editing[key];
                const isSavingCell = savingCells[key];
                const isCellCustom = !!cell?.factorId;
                const defs = zt.default_factors?.[st.slug];
                return (
                  <td
                    key={st.slug}
                    className={`px-2 py-2 border-b border-slate-100 align-top ${isCellCustom ? 'bg-blue-50/40' : ''}`}
                  >
                    {isEditingCell ? (
                      <div className="space-y-1.5 min-w-[130px]">
                        {(['saturation', 'attendance', 'resource'] as const).map(field => (
                          <div key={field} className="flex items-center gap-1">
                            <span className="text-[10px] text-slate-400 w-4 uppercase">{field[0]}</span>
                            <input
                              type="number"
                              step={0.1}
                              min={0}
                              max={2}
                              value={cell?.[field] ?? 0}
                              onChange={(e) => handleFieldChange(zt.slug, st.slug, field, e.target.value)}
                              className="w-14 px-1 py-0.5 border border-slate-200 rounded text-xs"
                            />
                          </div>
                        ))}
                        <div className="flex items-center gap-1">
                          <span className="text-[10px] text-slate-400 w-4">P</span>
                          <input
                            type="number"
                            min={0}
                            max={100}
                            value={cell?.priority ?? 0}
                            onChange={(e) => handleFieldChange(zt.slug, st.slug, 'priority', e.target.value)}
                            className="w-14 px-1 py-0.5 border border-slate-200 rounded text-xs"
                          />
                        </div>
                        <div className="flex gap-2 pt-1">
                          <button
                            onClick={() => saveCell(zt.slug, st.slug)}
                            disabled={isSavingCell}
                            className="flex items-center gap-0.5 text-[10px] text-emerald-600 hover:text-emerald-800 font-medium"
                          >
                            {isSavingCell ? <span>...</span> : <><Check className="w-3 h-3" />Guardar</>}
                          </button>
                          <button
                            onClick={() => setEditing(prev => ({ ...prev, [key]: false }))}
                            className="flex items-center gap-0.5 text-[10px] text-slate-400 hover:text-slate-600"
                          >
                            <X className="w-3 h-3" />Cerrar
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div
                        className="space-y-0.5 cursor-pointer hover:bg-slate-50 rounded p-1 -m-1"
                        onClick={() => setEditing(prev => ({ ...prev, [key]: true }))}
                      >
                        <div className="flex items-center gap-1">
                          <span className="text-[10px] text-slate-400 w-3">S</span>
                          <span className={`text-xs font-mono ${cell?.saturation !== defs?.saturation ? 'text-blue-600 font-semibold' : 'text-slate-600'}`}>
                            {cell?.saturation.toFixed(1)}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-[10px] text-slate-400 w-3">A</span>
                          <span className={`text-xs font-mono ${cell?.attendance !== defs?.attendance ? 'text-blue-600 font-semibold' : 'text-slate-600'}`}>
                            {cell?.attendance.toFixed(1)}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-[10px] text-slate-400 w-3">R</span>
                          <span className={`text-xs font-mono ${cell?.resource !== defs?.resource ? 'text-blue-600 font-semibold' : 'text-slate-600'}`}>
                            {cell?.resource.toFixed(1)}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-[10px] text-slate-400 w-3">P</span>
                          <span className="text-xs font-mono text-slate-600">{cell?.priority}</span>
                        </div>
                        {isCellCustom && (
                          <button
                            onClick={(e) => { e.stopPropagation(); resetCell(zt.slug, st.slug); }}
                            className="mt-1 text-[9px] text-slate-400 hover:text-red-500 flex items-center gap-0.5"
                          >
                            <RotateCcw className="w-2.5 h-2.5" />default
                          </button>
                        )}
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
