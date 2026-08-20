import React from 'react';
import {
  UtensilsCrossed, Droplets, Tent, DoorOpen, Music, MapPin,
  AlertTriangle, Users, RefreshCw, ShieldBan, Clock,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ZoneStateItem } from '../../../hooks/useContextEngine';

const ZONE_TYPE_ICONS: Record<string, LucideIcon> = {
  puesto_comida: UtensilsCrossed,
  comida: UtensilsCrossed,
  bano: Droplets,
  banos: Droplets,
  hidratacion: Droplets,
  emergencia: Tent,
  salud: Tent,
  ingreso: DoorOpen,
  escenario: Music,
};

function getZoneIcon(type: string): LucideIcon {
  return ZONE_TYPE_ICONS[type] || MapPin;
}

function getSaturationLevel(value: number): {
  label: string;
  color: string;
  bgLight: string;
  barColor: string;
  textColor: string;
  borderColor: string;
} {
  if (value < 0.3) {
    return {
      label: 'Baja',
      color: '#16a34a',
      bgLight: 'bg-emerald-50',
      barColor: 'bg-emerald-500',
      textColor: 'text-emerald-700',
      borderColor: 'border-emerald-200',
    };
  }
  if (value < 0.6) {
    return {
      label: 'Media',
      color: '#ca8a04',
      bgLight: 'bg-amber-50',
      barColor: 'bg-amber-500',
      textColor: 'text-amber-700',
      borderColor: 'border-amber-200',
    };
  }
  if (value < 0.8) {
    return {
      label: 'Alta',
      color: '#ea580c',
      bgLight: 'bg-orange-50',
      barColor: 'bg-orange-500',
      textColor: 'text-orange-700',
      borderColor: 'border-orange-200',
    };
  }
  return {
    label: 'Colapsado',
    color: '#dc2626',
    bgLight: 'bg-red-50',
    barColor: 'bg-red-600',
    textColor: 'text-red-700',
    borderColor: 'border-red-200',
  };
}

export interface ZoneCardZone extends ZoneStateItem {
  name?: string;
}

interface ZoneCardProps {
  zone: ZoneCardZone;
}

export const ZoneCard = React.memo(function ZoneCard({ zone }: ZoneCardProps) {
  const satVal = zone.saturation_level ?? 0;
  const satLevel = getSaturationLevel(satVal);
  const IconComponent = getZoneIcon(zone.type || zone.subtipo || '');
  const isHighDemand = satVal >= 0.8;
  const displayName = zone.name || zone.type || 'Zona';
  const displayType = (zone.type || zone.subtipo || '').replace(/_/g, ' ');

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border ${satLevel.borderColor} ${satLevel.bgLight} p-4 transition-shadow hover:shadow-md`}
      role="region"
      aria-label={`Zona ${displayName}, saturación ${satLevel.label}`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${satLevel.bgLight} border ${satLevel.borderColor}`}
            style={{ color: satLevel.color }}
          >
            <IconComponent size={20} strokeWidth={2} aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold text-slate-800 truncate">{displayName}</p>
            <p className="text-[10px] font-medium text-slate-500 capitalize">{displayType}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {zone.active_restriction && zone.active_restriction !== 'OPEN' && (
            <span
              className="inline-flex items-center gap-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full text-amber-700 border-amber-300 bg-amber-50"
              aria-label={`Restricción: ${zone.active_restriction}`}
            >
              <ShieldBan size={11} aria-hidden="true" />
              {zone.active_restriction}
            </span>
          )}
          <span
            className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${satLevel.textColor} ${satLevel.borderColor} ${satLevel.bgLight}`}
            aria-label={`Saturación: ${satLevel.label}`}
          >
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0"
              style={{ backgroundColor: satLevel.color }}
              aria-hidden="true"
            />
            {satLevel.label}
          </span>
        </div>
      </div>

      <div className="mb-3">
        <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden" role="progressbar" aria-valuenow={Math.round(satVal * 100)} aria-valuemin={0} aria-valuemax={100} aria-label={`Saturación ${Math.round(satVal * 100)}%`}>
          <div
            className={`h-full rounded-full transition-all duration-500 ${satLevel.barColor}`}
            style={{ width: `${Math.min(satVal * 100, 100)}%` }}
          />
        </div>
      </div>

      {isHighDemand && (
        <div className="flex items-center gap-1.5 mb-2">
          <AlertTriangle size={14} className="text-red-600 shrink-0" aria-hidden="true" />
          <span className="text-xs font-bold text-red-700 uppercase tracking-wide">Alta demanda</span>
        </div>
      )}

      <div className="grid grid-cols-3 gap-2">
        <div className="bg-white/70 rounded-lg p-2 text-center border border-slate-100">
          <Users size={14} className="text-slate-400 mx-auto mb-0.5" aria-hidden="true" />
          <div className="text-xs font-bold text-slate-700">{satVal.toFixed(2)}</div>
          <div className="text-[9px] text-slate-400 font-medium">Saturación</div>
        </div>
        <div className="bg-white/70 rounded-lg p-2 text-center border border-slate-100">
          <RefreshCw size={14} className="text-slate-400 mx-auto mb-0.5" aria-hidden="true" />
          <div className="text-xs font-bold text-slate-700">{(zone.confidence ?? 0).toFixed(2)}</div>
          <div className="text-[9px] text-slate-400 font-medium">Confianza</div>
        </div>
        <div className="bg-white/70 rounded-lg p-2 text-center border border-slate-100">
          <Clock size={14} className="text-slate-400 mx-auto mb-0.5" aria-hidden="true" />
          <div className="text-xs font-bold text-slate-700">{zone.availability ?? '—'}</div>
          <div className="text-[9px] text-slate-400 font-medium">Disponibilidad</div>
        </div>
      </div>
    </div>
  );
});