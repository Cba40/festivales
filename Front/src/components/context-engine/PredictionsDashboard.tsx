import { useState, useEffect } from 'react';
import { RefreshCw, Activity, Users, Wrench } from 'lucide-react';
import { EVENT_ID } from './constants';
import { usePredictions, useAutoRefresh } from '../../hooks/useContextEngine';
import type { ZonePredictionDTO } from '../../hooks/useContextEngine';

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

interface PredictionsDashboardProps {
  eventId?: string;
  autoRefreshMs?: number;
}

export function PredictionsDashboard({ eventId, autoRefreshMs = 15000 }: PredictionsDashboardProps) {
  const eid = eventId || EVENT_ID;
  const { data, loading, error, refresh } = usePredictions(eid);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useAutoRefresh(refresh, autoRefreshMs, autoRefresh);

  const zonas: ZonePredictionDTO[] = data?.zonas ?? [];

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

      {zonas.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-700">Zonas ({zonas.length})</h3>
          {zonas.map(zona => {
            const satVal = zona.prediccion.saturation_predicha;
            return (
              <div key={zona.id} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <span className="text-sm font-semibold text-slate-800">{zona.name}</span>
                    <span className="ml-2 text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">{zona.type}</span>
                  </div>
                  <div className="flex items-center gap-2">
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
                    <div className="text-xs font-semibold text-slate-700">{zona.prediccion.saturation_predicha.toFixed(2)}</div>
                    <div className="text-[9px] text-slate-400">Saturación</div>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-2 text-center">
                    <Users className="w-3.5 h-3.5 text-slate-400 mx-auto mb-0.5" />
                    <div className="text-xs font-semibold text-slate-700">{zona.prediccion.attendance_predicha.toFixed(2)}</div>
                    <div className="text-[9px] text-slate-400">Afluencia</div>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-2 text-center">
                    <Wrench className="w-3.5 h-3.5 text-slate-400 mx-auto mb-0.5" />
                    <div className="text-xs font-semibold text-slate-700">{zona.prediccion.recurso_requerido.toFixed(2)}</div>
                    <div className="text-[9px] text-slate-400">Recursos</div>
                  </div>
                </div>

                {zona.factores && (
                  <details className="mt-2">
                    <summary className="text-[10px] text-slate-400 cursor-pointer hover:text-slate-600">Factores</summary>
                    <div className="mt-1 grid grid-cols-4 gap-2 text-[10px] text-slate-500">
                      <div>S: {zona.factores.saturation.toFixed(2)}</div>
                      <div>A: {zona.factores.attendance.toFixed(2)}</div>
                      <div>R: {zona.factores.resource.toFixed(2)}</div>
                      <div>P: {zona.factores.priority}</div>
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
