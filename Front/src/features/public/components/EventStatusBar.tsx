import { useEffect } from 'react';
import { AlertTriangle, CheckCircle, Clock, RefreshCw } from 'lucide-react';
import { usePredictions, useAutoRefresh } from '../../../hooks/useContextEngine';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || '';

interface EventStatusBarProps {
  autoRefreshMs?: number;
}

export function EventStatusBar({ autoRefreshMs = 30000 }: EventStatusBarProps) {
  const { data, loading, error, refresh } = usePredictions(EVENT_ID);

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

  const estado = data?.estado_actual;
  const override = data?.override_activo;

  if (!estado) {
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

  return (
    <div className="px-4 py-3 border-b flex items-center gap-3 bg-white" style={{ borderLeft: `4px solid ${estado.color || '#94a3b8'}` }}>
      <div
        className="w-3 h-3 rounded-full shrink-0"
        style={{ backgroundColor: estado.color || '#94a3b8' }}
        role="img"
        aria-label={`Estado: ${estado.name}`}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-bold text-slate-800 truncate">{estado.name}</p>
          {override && (
            <span className="text-[10px] font-bold uppercase bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full border border-amber-200 shrink-0">
              Override
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500">
          {override
            ? 'Override activo — estado forzado por el operador'
            : 'Predicción en tiempo real basada en el estado actual del evento'}
        </p>
      </div>
      <div className="shrink-0">
        <CheckCircle size={16} className="text-emerald-500" aria-label="Activo" />
      </div>
    </div>
  );
}
