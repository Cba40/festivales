import { useState, useEffect } from 'react';
import { RefreshCw, Activity, Users, ShieldBan, Clock, Info } from 'lucide-react';
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

const NO_DATA = 'N/A';

interface ZoneStateStyle {
  label: string;
  color: string;
}

const STATE_STYLES: Record<string, ZoneStateStyle> = {
  LOW_DEMAND: { label: 'Baja', color: 'bg-emerald-500' },
  MODERATE: { label: 'Media', color: 'bg-amber-500' },
  HIGH_DEMAND: { label: 'Alta', color: 'bg-orange-500' },
  CLOSED: { label: 'Colapsado', color: 'bg-red-600' },
  REGULATED: { label: 'Regulada', color: 'bg-orange-500' },
};

function getStateStyle(state: string): ZoneStateStyle {
  return STATE_STYLES[state] ?? { label: state.replace(/_/g, ' '), color: 'bg-slate-400' };
}

function getSaturationBarColor(value: number): string {
  if (value < 0.3) return 'bg-emerald-500';
  if (value < 0.6) return 'bg-amber-500';
  if (value < 0.8) return 'bg-orange-500';
  return 'bg-red-600';
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
          {data && (
            <span
              className={`flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full ${
                data.knowledge_model_version_id
                  ? 'bg-indigo-50 text-indigo-600 border border-indigo-200'
                  : 'bg-slate-100 text-slate-500 border border-slate-200'
              }`}
              title="Versión del modelo de conocimiento usado para esta predicción"
            >
              <RefreshCw className="w-3 h-3" />
              KM {data.knowledge_model_version_id
                ? data.knowledge_model_version_id.slice(0, 8)
                : 'Sin versión'}
            </span>
          )}
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
            const statusStyle = getStateStyle(zs.operational_state);
            const restriction = RESTRICTION_LABELS[zs.active_restriction] || zs.active_restriction;
            const missingDetailedMetrics =
              zs.saturation_level == null &&
              zs.availability == null &&
              zs.confidence == null &&
              zs.estimated_wait == null;
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
                    <div className={`w-2.5 h-2.5 rounded-full ${statusStyle.color}`} />
                    <span className="text-xs font-medium text-slate-600">{statusStyle.label}</span>
                  </div>
                </div>

                {missingDetailedMetrics && (
                  <div className="mb-2">
                    <span
                      className="inline-flex items-center gap-1 text-[10px] font-semibold text-indigo-600 bg-indigo-50 border border-indigo-200 rounded-full px-2 py-0.5"
                      title="El motor aún no ejecuta un modelo especializado que produzca saturación, disponibilidad y confianza para esta zona."
                    >
                      <Info size={11} />
                      Métricas detalladas pendientes de modelo especializado
                    </span>
                  </div>
                )}

                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden mb-3">
                  <div
                    className={`h-full rounded-full transition-all ${
                      zs.saturation_level != null ? getSaturationBarColor(zs.saturation_level) : 'bg-slate-200'
                    }`}
                    style={{
                      width: `${zs.saturation_level != null ? Math.min(zs.saturation_level * 100, 100) : 0}%`,
                    }}
                  />
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-slate-50 rounded-lg p-2 text-center">
                    <Activity className="w-3.5 h-3.5 text-slate-400 mx-auto mb-0.5" />
                    <div className="text-xs font-semibold text-slate-700">
                      {zs.saturation_level != null ? zs.saturation_level.toFixed(2) : NO_DATA}
                    </div>
                    <div className="text-[9px] text-slate-400">Saturación</div>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-2 text-center">
                    <Users className="w-3.5 h-3.5 text-slate-400 mx-auto mb-0.5" />
                    <div className="text-xs font-semibold text-slate-700">
                      {zs.availability != null ? zs.availability : NO_DATA}
                    </div>
                    <div className="text-[9px] text-slate-400">Disponibilidad</div>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-2 text-center">
                    <RefreshCw className="w-3.5 h-3.5 text-slate-400 mx-auto mb-0.5" />
                    <div className="text-xs font-semibold text-slate-700">
                      {zs.confidence != null ? zs.confidence.toFixed(2) : NO_DATA}
                    </div>
                    <div className="text-[9px] text-slate-400">Confianza</div>
                  </div>
                </div>

                <div className="mt-2 flex items-center gap-3 text-[10px] text-slate-400">
                  <span className="capitalize">Estado: {zs.operational_state.replace(/_/g, ' ')}</span>
                  <span className="flex items-center gap-1">
                    <Clock size={11} />
                    Espera: {zs.estimated_wait != null ? `${zs.estimated_wait} min` : NO_DATA}
                  </span>
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