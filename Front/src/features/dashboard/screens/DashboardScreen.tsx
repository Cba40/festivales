// src/features/dashboard/screens/DashboardScreen.tsx

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  RefreshCw,
  AlertTriangle,
  Plus,
  Clock,
  Loader2,
  MapPin,
  ChevronRight,
  Shield,
} from 'lucide-react';
import { useDashboardSync } from '../hooks/useDashboardSync';
import { useIncidentMutations } from '../hooks/useIncidentMutations';
import { ZoneStatusCard } from '../components/ZoneStatusCard';
import type { Incident, IncidentSeverity } from '../types';

// ── Helpers ──

const SEVERITY_STYLES: Record<IncidentSeverity, { dot: string; bg: string; border: string }> = {
  baja: { dot: 'bg-emerald-500', bg: 'bg-emerald-50', border: 'border-emerald-200/60' },
  media: { dot: 'bg-amber-500', bg: 'bg-amber-50', border: 'border-amber-200/60' },
  alta: { dot: 'bg-orange-500', bg: 'bg-orange-50', border: 'border-orange-200/60' },
  critica: { dot: 'bg-red-500', bg: 'bg-red-50', border: 'border-red-300/60' },
};

const TYPE_LABELS: Record<string, string> = {
  congestion: '🚗 Congestión',
  closure: '🚧 Cierre',
  emergency: '🚨 Emergencia',
};

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  abierto: { label: 'Abierto', color: 'text-red-600 bg-red-50' },
  en_progreso: { label: 'En progreso', color: 'text-amber-600 bg-amber-50' },
  resuelto: { label: 'Resuelto', color: 'text-emerald-600 bg-emerald-50' },
};

function timeAgo(isoDate: string): string {
  const diffMs = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'hace un momento';
  if (mins < 60) return `hace ${mins} min`;
  const hours = Math.floor(mins / 60);
  return `hace ${hours}h`;
}

// ── Incident card (inline) ──

function IncidentCard({ incident }: { incident: Incident }) {
  const { resolveIncident } = useIncidentMutations();
  const sev = SEVERITY_STYLES[incident.severity];
  const status = STATUS_LABELS[incident.status] ?? STATUS_LABELS.abierto;

  return (
    <div className={`rounded-xl border p-3.5 transition-all duration-200 hover:shadow-sm ${sev.bg} ${sev.border}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`w-2 h-2 rounded-full shrink-0 ${sev.dot} ${incident.severity === 'critica' ? 'animate-pulse' : ''}`} />
          <span className="text-xs font-bold text-slate-800 truncate">
            {TYPE_LABELS[incident.type] ?? incident.type}
          </span>
        </div>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${status.color}`}>
          {status.label}
        </span>
      </div>

      <p className="text-xs text-slate-600 leading-relaxed mb-2 line-clamp-2">
        {incident.description}
      </p>

      <div className="flex items-center justify-between">
        <span className="text-[10px] text-slate-400 flex items-center gap-1">
          <Clock size={10} />
          {timeAgo(incident.createdAt)}
        </span>
        {incident.status !== 'resuelto' && (
          <button
            onClick={() => resolveIncident(incident.id)}
            className="text-[10px] font-bold text-primary hover:text-primary/80 transition-colors cursor-pointer"
          >
            Resolver →
          </button>
        )}
      </div>
    </div>
  );
}

// ── Main Screen ──

export default function DashboardScreen() {
  const navigate = useNavigate();
  const { zones, incidents, loading, error, lastSync, refresh } = useDashboardSync();

  useEffect(() => {
    refresh();
  }, [refresh]);

  const activeIncidents = incidents.filter((i) => i.status !== 'resuelto');
  const zonesCollapsed = zones.filter((z) => z.saturation === 'colapsado').length;
  const zonesHigh = zones.filter((z) => z.saturation === 'alto').length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-blue-50/30">
      {/* ── Header ── */}
      <header className="sticky top-0 z-30 backdrop-blur-xl bg-white/80 border-b border-slate-200/60 px-4 sm:px-6 lg:px-8 py-4">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center shadow-lg shadow-primary/20">
              <Shield size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-black text-slate-900 tracking-tight">
                Operación Territorial
              </h1>
              <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
                <LayoutDashboard size={12} />
                Dashboard Municipal · MVP
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {lastSync && (
              <span className="text-[10px] text-slate-400 hidden sm:inline-flex items-center gap-1">
                <Clock size={10} />
                Sync: {new Date(lastSync).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
            <button
              onClick={() => refresh()}
              disabled={loading}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold
                bg-white border border-slate-200 text-slate-700
                hover:bg-slate-50 hover:border-slate-300
                disabled:opacity-50 transition-all duration-200 cursor-pointer"
            >
              {loading ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <RefreshCw size={14} />
              )}
              Sincronizar
            </button>
          </div>
        </div>
      </header>

      {/* ── Content ── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Error banner */}
        {error && (
          <div className="mb-4 flex items-center gap-2 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700">
            <AlertTriangle size={16} />
            {error}
          </div>
        )}

        {/* Summary stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="bg-white rounded-2xl border border-slate-200/60 p-4 shadow-sm">
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Zonas</p>
            <p className="text-2xl font-black text-slate-900">{zones.length}</p>
          </div>
          <div className="bg-white rounded-2xl border border-slate-200/60 p-4 shadow-sm">
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Incidentes</p>
            <p className="text-2xl font-black text-orange-600">{activeIncidents.length}</p>
          </div>
          <div className="bg-white rounded-2xl border border-slate-200/60 p-4 shadow-sm">
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Sat. Alta</p>
            <p className="text-2xl font-black text-amber-600">{zonesHigh}</p>
          </div>
          <div className="bg-white rounded-2xl border border-slate-200/60 p-4 shadow-sm">
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Colapsadas</p>
            <p className="text-2xl font-black text-red-600">{zonesCollapsed}</p>
          </div>
        </div>

        {/* 2-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Col 1: Zones (3/5 width) */}
          <section className="lg:col-span-3 space-y-3">
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-sm font-black text-slate-700 uppercase tracking-wider flex items-center gap-2">
                <MapPin size={16} className="text-primary" />
                Zonas Operativas
              </h2>
              <button
                onClick={() => navigate('/dashboard/zones')}
                className="text-[11px] font-bold text-primary hover:text-primary/80 transition-colors flex items-center gap-1 cursor-pointer"
              >
                Ver todas
                <ChevronRight size={14} />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[calc(100vh-320px)] overflow-y-auto pr-1 scrollbar-thin">
              {zones.map((zone) => (
                <ZoneStatusCard key={zone.id} zone={zone} />
              ))}
            </div>
          </section>

          {/* Col 2: Incidents (2/5 width) */}
          <section className="lg:col-span-2 space-y-3">
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-sm font-black text-slate-700 uppercase tracking-wider flex items-center gap-2">
                <AlertTriangle size={16} className="text-orange-500" />
                Incidentes Activos
                {activeIncidents.length > 0 && (
                  <span className="ml-1 px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 text-[10px] font-bold">
                    {activeIncidents.length}
                  </span>
                )}
              </h2>
            </div>

            <div className="space-y-2 max-h-[calc(100vh-400px)] overflow-y-auto pr-1">
              {activeIncidents.length === 0 ? (
                <div className="text-center py-10 bg-white rounded-2xl border border-slate-200/60">
                  <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center mx-auto mb-3">
                    <Shield size={24} className="text-emerald-500" />
                  </div>
                  <p className="text-sm font-bold text-slate-700">Sin incidentes activos</p>
                  <p className="text-xs text-slate-400 mt-1">Todo opera con normalidad</p>
                </div>
              ) : (
                activeIncidents.map((inc) => (
                  <IncidentCard key={inc.id} incident={inc} />
                ))
              )}
            </div>

            {/* Reportar button */}
            <button
              onClick={() => navigate('/dashboard/report')}
              className="
                w-full flex items-center justify-center gap-2.5 px-5 py-3.5 rounded-2xl
                bg-gradient-to-r from-primary to-blue-600 text-white
                text-sm font-bold uppercase tracking-wide
                shadow-lg shadow-primary/25
                hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-0.5
                active:scale-[0.98]
                transition-all duration-300 cursor-pointer
              "
            >
              <Plus size={18} />
              Reportar Incidente
            </button>
          </section>
        </div>
      </main>
    </div>
  );
}
