import { useEffect } from 'react';
import { RefreshCw, Layers } from 'lucide-react';
import { usePredictions, useAutoRefresh } from '../../../hooks/useContextEngine';
import { ZoneCard } from './ZoneCard';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || '';

interface ZoneListProps {
  autoRefreshMs?: number;
}

export function ZoneList({ autoRefreshMs = 30000 }: ZoneListProps) {
  const { data, loading, error, refresh } = usePredictions(EVENT_ID);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useAutoRefresh(refresh, autoRefreshMs, !!EVENT_ID);

  if (loading && !data) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 mb-3">
          <Layers size={16} className="text-slate-400" />
          <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wide">Zonas del evento</h2>
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-2xl border border-slate-200 bg-white p-4 animate-pulse">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-10 h-10 rounded-xl bg-slate-200" />
              <div className="flex-1">
                <div className="h-4 bg-slate-200 rounded w-28 mb-1" />
                <div className="h-3 bg-slate-200 rounded w-20" />
              </div>
            </div>
            <div className="h-2 bg-slate-200 rounded-full mb-3" />
            <div className="grid grid-cols-3 gap-2">
              <div className="h-12 bg-slate-100 rounded-lg" />
              <div className="h-12 bg-slate-100 rounded-lg" />
              <div className="h-12 bg-slate-100 rounded-lg" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Layers size={16} className="text-slate-400" />
          <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wide">Zonas del evento</h2>
        </div>
        <div className="text-center py-8 bg-white rounded-2xl border border-slate-200">
          <p className="text-sm text-slate-500 mb-2">No se pudieron cargar las zonas</p>
          <button
            onClick={() => refresh()}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary bg-primary/10 px-3 py-2 rounded-lg hover:bg-primary/20 transition-colors"
          >
            <RefreshCw size={14} />
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  const zonas = data?.zonas ?? [];

  if (zonas.length === 0) {
    return (
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Layers size={16} className="text-slate-400" />
          <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wide">Zonas del evento</h2>
        </div>
        <div className="text-center py-8 bg-white rounded-2xl border border-slate-200">
          <Layers size={32} className="text-slate-300 mx-auto mb-2" />
          <p className="text-sm font-semibold text-slate-500">Sin zonas disponibles</p>
          <p className="text-xs text-slate-400 mt-1">Las zonas aparecerán cuando la jornada esté activa</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Layers size={16} className="text-slate-400" />
          <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wide">
            Zonas del evento
          </h2>
          <span className="text-[10px] font-bold text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded-full">
            {zonas.length}
          </span>
        </div>
        <button
          onClick={() => refresh()}
          disabled={loading}
          className="flex items-center gap-1 text-[10px] font-semibold text-slate-400 hover:text-slate-600 transition-colors disabled:opacity-50"
          aria-label="Actualizar zonas"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          {loading ? 'Actualizando...' : 'Actualizar'}
        </button>
      </div>
      <div className="space-y-3">
        {zonas.map((zone) => (
          <ZoneCard key={zone.id} zone={zone} />
        ))}
      </div>
    </div>
  );
}
