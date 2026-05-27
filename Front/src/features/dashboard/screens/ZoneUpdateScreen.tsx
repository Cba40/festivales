// src/features/dashboard/screens/ZoneUpdateScreen.tsx

import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Filter, MapPin } from 'lucide-react';
import { useAppStore } from '@/core/state/store';
import { ZoneStatusCard } from '../components/ZoneStatusCard';
import type { ZoneType } from '../types';

// ── Opciones de filtro ──

const ZONE_TYPE_FILTERS: { value: ZoneType | 'todas'; label: string }[] = [
  { value: 'todas', label: 'Todas' },
  { value: 'estacionamiento', label: '🚗 Estacionamiento' },
  { value: 'transporte', label: '🚌 Transporte' },
  { value: 'comida', label: '🍽 Comida' },
  { value: 'descanso', label: '🌙 Descanso' },
  { value: 'servicios', label: '🔧 Servicios' },
  { value: 'emergencia', label: '🚨 Emergencia' },
];

export default function ZoneUpdateScreen() {
  const navigate = useNavigate();
  const zones = useAppStore((s) => s.zones);
  const [filter, setFilter] = useState<ZoneType | 'todas'>('todas');

  const filteredZones = useMemo(() => {
    if (filter === 'todas') return zones;
    return zones.filter((z) => z.type === filter);
  }, [zones, filter]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-blue-50/30">
      {/* Header */}
      <header className="sticky top-0 z-30 backdrop-blur-xl bg-white/80 border-b border-slate-200/60 px-4 sm:px-6 lg:px-8 py-4">
        <div className="max-w-7xl mx-auto flex items-center gap-4">
          <button
            onClick={() => navigate('/dashboard')}
            className="w-9 h-9 rounded-xl bg-slate-100 hover:bg-slate-200 flex items-center justify-center transition-colors cursor-pointer"
          >
            <ArrowLeft size={18} className="text-slate-600" />
          </button>
          <div>
            <h1 className="text-lg font-black text-slate-900 tracking-tight flex items-center gap-2">
              <MapPin size={20} className="text-primary" />
              Gestión de Zonas
            </h1>
            <p className="text-[11px] text-slate-500">
              {filteredZones.length} zonas · Actualización de saturación en tiempo real
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Filters */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Filter size={14} className="text-slate-400" />
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Filtrar por tipo
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {ZONE_TYPE_FILTERS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setFilter(opt.value)}
                className={`
                  px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 cursor-pointer
                  ${filter === opt.value
                    ? 'bg-primary text-white shadow-md shadow-primary/20'
                    : 'bg-white border border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50'
                  }
                `}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Zones grid */}
        {filteredZones.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-slate-200/60">
            <MapPin size={32} className="text-slate-300 mx-auto mb-3" />
            <p className="text-sm font-bold text-slate-600">No hay zonas de este tipo</p>
            <p className="text-xs text-slate-400 mt-1">Seleccioná otro filtro para ver zonas disponibles</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredZones.map((zone) => (
              <ZoneStatusCard key={zone.id} zone={zone} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
