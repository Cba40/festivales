// src/features/dashboard/components/ZoneStatusCard.tsx

import { useState } from 'react';
import {
  MapPin,
  Car,
  Bus,
  UtensilsCrossed,
  Moon,
  Wrench,
  Siren,
  ChevronDown,
  Loader2,
} from 'lucide-react';
import type { Zone, SaturationLevel } from '../types';
import { useZoneMutations } from '../hooks/useZoneMutations';

// ── Mapas visuales ──

const SATURATION_STYLES: Record<SaturationLevel, { bg: string; text: string; badge: string; dot: string }> = {
  bajo: {
    bg: 'bg-emerald-50 border-emerald-200/60',
    text: 'text-emerald-700',
    badge: 'bg-emerald-100 text-emerald-700 ring-emerald-500/20',
    dot: 'bg-emerald-500',
  },
  medio: {
    bg: 'bg-amber-50 border-amber-200/60',
    text: 'text-amber-700',
    badge: 'bg-amber-100 text-amber-700 ring-amber-500/20',
    dot: 'bg-amber-500',
  },
  alto: {
    bg: 'bg-orange-50 border-orange-200/60',
    text: 'text-orange-700',
    badge: 'bg-orange-100 text-orange-700 ring-orange-500/20',
    dot: 'bg-orange-500',
  },
  colapsado: {
    bg: 'bg-red-50 border-red-300/60',
    text: 'text-red-700',
    badge: 'bg-red-100 text-red-700 ring-red-500/20',
    dot: 'bg-red-500',
  },
};

const SATURATION_LABELS: Record<SaturationLevel, string> = {
  bajo: 'Bajo',
  medio: 'Medio',
  alto: 'Alto',
  colapsado: 'Colapsado',
};

const TYPE_ICONS: Record<string, typeof MapPin> = {
  estacionamiento: Car,
  transporte: Bus,
  comida: UtensilsCrossed,
  descanso: Moon,
  servicios: Wrench,
  emergencia: Siren,
};

const SATURATION_OPTIONS: SaturationLevel[] = ['bajo', 'medio', 'alto', 'colapsado'];

interface ZoneStatusCardProps {
  zone: Zone;
}

export function ZoneStatusCard({ zone }: ZoneStatusCardProps) {
  const { updateSaturation, updating } = useZoneMutations();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const style = SATURATION_STYLES[zone.saturation];
  const Icon = TYPE_ICONS[zone.type] ?? MapPin;
  const isUpdating = updating === zone.id;
  const usagePercent = zone.capacity > 0
    ? Math.round(((zone.capacity - zone.availableCapacity) / zone.capacity) * 100)
    : 0;

  const handleSaturationChange = async (newSat: SaturationLevel) => {
    setDropdownOpen(false);
    if (newSat !== zone.saturation) {
      await updateSaturation(zone.id, newSat);
    }
  };

  return (
    <div
      className={`
        relative rounded-2xl border p-4 transition-all duration-300
        ${style.bg}
        ${isUpdating ? 'opacity-70 scale-[0.98]' : 'hover:shadow-md hover:-translate-y-0.5'}
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${style.badge} ring-1 ring-inset`}>
            <Icon size={18} />
          </div>
          <div className="min-w-0">
            <h4 className="text-sm font-bold text-slate-800 truncate">
              {zone.name}
            </h4>
            <p className="text-[11px] text-slate-500 capitalize">
              {zone.type} · {zone.status}
            </p>
          </div>
        </div>

        {/* Saturation badge */}
        <span className={`
          inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wide
          ${style.badge} ring-1 ring-inset shrink-0
        `}>
          <span className={`w-1.5 h-1.5 rounded-full ${style.dot} ${zone.saturation === 'colapsado' ? 'animate-pulse' : ''}`} />
          {SATURATION_LABELS[zone.saturation]}
        </span>
      </div>

      {/* Capacity bar */}
      <div className="mb-3">
        <div className="flex justify-between text-[11px] text-slate-500 mb-1">
          <span>Capacidad usada</span>
          <span className="font-semibold text-slate-700">
            {zone.capacity - zone.availableCapacity} / {zone.capacity}
          </span>
        </div>
        <div className="h-2 bg-slate-200/60 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              usagePercent >= 90
                ? 'bg-red-500'
                : usagePercent >= 70
                  ? 'bg-orange-500'
                  : usagePercent >= 50
                    ? 'bg-amber-500'
                    : 'bg-emerald-500'
            }`}
            style={{ width: `${usagePercent}%` }}
          />
        </div>
      </div>

      {/* Dropdown to change saturation */}
      <div className="relative">
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          disabled={isUpdating}
          className={`
            w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold
            border border-slate-200/80 bg-white/70 backdrop-blur-sm
            transition-all duration-200
            ${isUpdating ? 'cursor-not-allowed' : 'hover:bg-white hover:border-slate-300 cursor-pointer'}
          `}
        >
          <span className="text-slate-600">
            {isUpdating ? 'Actualizando…' : 'Cambiar saturación'}
          </span>
          {isUpdating ? (
            <Loader2 size={14} className="animate-spin text-slate-400" />
          ) : (
            <ChevronDown
              size={14}
              className={`text-slate-400 transition-transform duration-200 ${dropdownOpen ? 'rotate-180' : ''}`}
            />
          )}
        </button>

        {dropdownOpen && (
          <div className="absolute z-20 top-full left-0 right-0 mt-1 bg-white rounded-xl border border-slate-200 shadow-lg overflow-hidden">
            {SATURATION_OPTIONS.map((sat) => {
              const s = SATURATION_STYLES[sat];
              const isActive = sat === zone.saturation;
              return (
                <button
                  key={sat}
                  onClick={() => handleSaturationChange(sat)}
                  className={`
                    w-full flex items-center gap-2.5 px-3 py-2.5 text-xs font-medium text-left
                    transition-colors duration-150
                    ${isActive
                      ? 'bg-slate-100 font-bold'
                      : 'hover:bg-slate-50 cursor-pointer'
                    }
                  `}
                >
                  <span className={`w-2 h-2 rounded-full ${s.dot}`} />
                  <span className={isActive ? 'text-slate-900' : 'text-slate-600'}>
                    {SATURATION_LABELS[sat]}
                  </span>
                  {isActive && (
                    <span className="ml-auto text-[10px] text-slate-400 font-normal">actual</span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
