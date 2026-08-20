import { useState, useEffect } from 'react';
import { RefreshCw, Activity, Users, ShieldBan, Clock } from 'lucide-react';
import { EVENT_ID } from './constants';
import { useTerritorialPrediction, useAutoRefresh } from '../../hooks/useContextEngine';
import type { ZoneStateItem } from '../../hooks/useContextEngine';
import { apiClient } from '../../core/api/client';
import { endpoints } from '../../core/api/endpoints';

const RESTRICTION_LABELS: Record<string, string> = {
  OPEN: 'Abierta',
  REGULATED: 'Regulada',
  CLOSED: 'Cerrada',
};

function getSaturationColor(value: number): string {
  if (value < 0.3) return 'bg-emerald-500';
  if (value < 0.6) return 'bg-amber-500';
  if (value < 0.8) return 'bg-orange-500';
  return 'bg-red-600';
}

function getSaturationLabel(value: number): string {
  if (value < 0.3) return 'Baja';
  if (value < 0.6) return 'Media';
  if (value < 0.8) return 'Alta';
  return 'Colapsado';
}

interface ZoneInfo {
  id: string;
  name: string;
  type: string;
  subtipo?: string | null;
}

interface PredictionsDashboardProps {
  eventId?: string;
  autoRefreshMs?: number;
}

export function PredictionsDashboard({ eventId, autoRefreshMs = 15000 }: PredictionsDashboardProps) {
  const eid = eventId || EVENT_ID;
  const { data, loading, error, refresh } = useTerritorialPrediction(eid);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [zonesById, setZonesById] = useState<Record<string, { name: string; type: string }>>({});

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    let cancelled = false;
    apiClient
      .get<ZoneInfo[]>(endpoints.zones.list(eid))
      .then((res) => {
        if (cancelled) return;
        const map: Record<string, { name: string; type: string }> = {};
        for (const z of res.data ?? []) {
          map[z.id] = { name: z.name, type: z.type };
        }
        setZonesById(map);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [eid]);

  useAutoRefresh(refresh, autoRefreshMs, autoRefresh);

  const zoneStates: ZoneStateItem[] = data?.zone_states ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Predicciones del motor</h2>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-slate-300"
            />
            Auto {autoRefreshMs / 1000}s
          </label>
          <button
            onClick={() => refresh()}
            disabled={loading}
            className="flex items-center gap-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-600 py-1.5 px-3 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Cargando...' : 'Actualizar'}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
      )}

      {!loading && !data && !error && (
        <div className="text-center py-8 text-slate-400 italic">Sin datos. Seleccioná una jornada activa.</div>
      )}

      {data && zoneStates.length === 0 && !error && (
        <div className="text-center py-8 text-slate-400 italic">
          No hay predicciones disponibles todavía. El evento aún no está activo.
        </div>
      )}

      {zoneStates.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-700">Zonas ({zoneStates.length})</h3>
          {zoneStates.map((zs) => {
            const zona = zonesById[zs.zone_id];
            const name = zona?.name || zs.type || 'Zona';
            const typeLabel = zona?.type || zs.type || 'desconocida';
            const satVal = zs.saturation_level ?? 0;
            const restriction = RESTRICTION_LABELS[zs.active_restriction] || zs.active_restriction;
            return (
              <div key={zs.zone_id} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <span className="text-sm font-semibold text-slate-800">{name}</span>
                    <span className="ml-2 text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">{typeLabel}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {zs.active_restriction !== 'OPEN' && (
                      <span className="flex items-center gap-1 text-[10px] font-bold text-amber-600 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
                        <ShieldBan size={11} />
                        {restriction}
                      </span>
                    )}
                    <div className={`w-2.5 h-2.5 rounded-full ${getSaturationColor(satVal)}`} />
                    <span className="text-xs font-medium text-slate-600">{getSaturationLabel(satVal)}</span>
                  </div>
                </div>

                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden mb-3">
                  <div
                    className={`h-full rounded-full transition-all ${getSaturationColor(satVal)}`}
                    style={{ width: `${Math.min(satVal * 100, 100)}%` }}
                  />
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-slate-50 rounded-lg p-2 text-center">
                    <Activity className="w-3.5 h-3.5 text-slate-400 mx-auto mb-0.5" />
                    <div className="text-xs font-semibold text-slate-700">{satVal.toFixed(2)}</div>
                    <div className="text-[9px] text-slate-400">Saturación</div>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-2 text-center">
                    <Users className="w-3.5 h-3.5 text-slate-400 mx-auto mb-0.5" />
                    <div className="text-xs font-semibold text-slate-700">{zs.availability ?? '—'}</div>
                    <div className="text-[9px] text-slate-400">Disponibilidad</div>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-2 text-center">
                    <RefreshCw className="w-3.5 h-3.5 text-slate-400 mx-auto mb-0.5" />
                    <div className="text-xs font-semibold text-slate-700">{(zs.confidence ?? 0).toFixed(2)}</div>
                    <div className="text-[9px] text-slate-400">Confianza</div>
                  </div>
                </div>

                <div className="mt-2 flex items-center gap-3 text-[10px] text-slate-400">
                  <span className="capitalize">Estado: {zs.operational_state.replace(/_/g, ' ')}</span>
                  {(zs.estimated_wait ?? 0) > 0 && (
                    <span className="flex items-center gap-1">
                      <Clock size={11} />
                      Espera: {zs.estimated_wait} min
                    </span>
                  )}
                </div>

                {zs.reasoning_factors && zs.reasoning_factors.length > 0 && (
                  <details className="mt-2">
                    <summary className="text-[10px] text-slate-400 cursor-pointer hover:text-slate-600">Factores de decisión</summary>
                    <div className="mt-1 space-y-1">
                      {zs.reasoning_factors.map((f, i) => (
                        <div key={i} className="text-[10px] text-slate-500">• {f}</div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}