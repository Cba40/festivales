import { useEffect } from 'react';
import { AlertTriangle, CheckCircle, Clock, RefreshCw, ShieldBan } from 'lucide-react';
import { useTerritorialPrediction, useAutoRefresh } from '../../../hooks/useContextEngine';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || '';

interface EventStatusBarProps {
  autoRefreshMs?: number;
}

export function EventStatusBar({ autoRefreshMs = 30000 }: EventStatusBarProps) {
  const { data, loading, error, refresh } = useTerritorialPrediction(EVENT_ID);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useAutoRefresh(refresh, autoRefreshMs, !!EVENT_ID);

  if (loading && !data) {
    return (
      <div className="px-4 py-3 bg-slate-100 border-b border-slate-200 flex items-center gap-3">
        <div className="w-4 h-4 rounded-full bg-slate-300 animate-pulse" />
        <div className="flex-1">
          <div className="h-4 bg-slate-200 rounded w-36 animate-pulse mb-1" />
          <div className="h-3 bg-slate-200 rounded w-24 animate-pulse" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 py-3 bg-red-50 border-b border-red-200 flex items-center gap-3">
        <AlertTriangle size={18} className="text-red-500 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-red-700">Información del evento no disponible</p>
          <p className="text-xs text-red-500 truncate">{error}</p>
        </div>
        <button
          onClick={() => refresh()}
          className="shrink-0 p-1.5 rounded-lg hover:bg-red-100 transition-colors"
          aria-label="Reintentar"
        >
          <RefreshCw size={16} className="text-red-500" />
        </button>
      </div>
    );
  }

  if (!data || data.zone_states.length === 0) {
    return (
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center gap-3">
        <Clock size={18} className="text-slate-400 shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-semibold text-slate-600">Evento no iniciado</p>
          <p className="text-xs text-slate-400">Las predicciones estarán disponibles cuando comience la jornada</p>
        </div>
      </div>
    );
  }

  const zones = data.zone_states;
  const avgSaturation = zones.reduce((sum, z) => sum + z.saturation_level, 0) / zones.length;
  const restrictedZones = zones.filter(z => z.active_restriction !== 'OPEN').length;
  const saturationPct = Math.round(avgSaturation * 100);
  const barColor = saturationPct > 75 ? 'bg-red-500' : saturationPct > 50 ? 'bg-amber-500' : 'bg-emerald-500';
  const dotColor = saturationPct > 75 ? 'bg-red-500' : saturationPct > 50 ? 'bg-amber-500' : 'bg-emerald-500';

  return (
    <div className="px-4 py-3 border-b flex items-center gap-3 bg-white border-l-4 border-l-emerald-500">
      <div className={`w-3 h-3 rounded-full shrink-0 ${dotColor}`} role="img" aria-label={`Saturación: ${saturationPct}%`} />
      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="flex items-center gap-2">
          <p className="text-sm font-bold text-slate-800">Territorio activo</p>
          <span className="text-[11px] font-semibold text-slate-400">{zones.length} zona{zones.length !== 1 ? 's' : ''}</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <div className="flex items-center gap-1.5">
            <div className={`h-1.5 w-16 rounded-full bg-slate-200 overflow-hidden`}>
              <div className={`h-full rounded-full ${barColor} transition-all`} style={{ width: `${saturationPct}%` }} />
            </div>
            <span>{saturationPct}% saturado</span>
          </div>
          {restrictedZones > 0 && (
            <span className="flex items-center gap-1">
              <ShieldBan size={12} className="text-amber-500" />
              {restrictedZones} restringida{restrictedZones !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <p className="text-[11px] text-slate-400">
          {data.timestamp ? `Actualizado ${new Date(data.timestamp).toLocaleTimeString()}` : ''}
        </p>
      </div>
      <div className="shrink-0">
        <CheckCircle size={16} className="text-emerald-500" aria-label="Activo" />
      </div>
    </div>
  );
}
