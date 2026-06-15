import React from 'react';
import { MapPin, Info, ArrowRight, Star, AlertCircle } from 'lucide-react';

interface ZonaCardProps {
  id: string;
  nombre: string;
  precio: string;
  estado: 'disponible' | 'alerta' | 'critico';
  recomendada?: boolean;
  modo: 'primaria' | 'fallback' | 'advertencia' | 'completa';
  capacidad: string;
  ubicacion?: string;
  onSelect: (id: string) => void;
}

export const ZonaCard = ({
  id,
  nombre,
  precio,
  estado,
  recomendada,
  modo,
  capacidad,
  ubicacion,
  onSelect
}: ZonaCardProps) => {

  const statusColors = {
    disponible: 'border-success/30 text-success',
    alerta: 'border-amber-500 text-amber-600',
    critico: 'border-danger/30 text-danger'
  };

  const isWarning = modo === 'advertencia' || estado === 'critico';

  return (
    <div 
      onClick={() => onSelect(id)}
      className={`
        relative overflow-hidden rounded-3xl p-5 transition-all duration-300 active:scale-95 cursor-pointer
        ${recomendada
          ? 'ring-4 ring-primary ring-offset-2 scale-105 z-10 bg-white shadow-2xl'
          : 'bg-white border border-slate-200 shadow-sm'}
        ${isWarning ? 'bg-red-50/50' : ''}
      `}
    >
      {recomendada && (
        <div className="absolute top-3 right-3 bg-primary text-white text-[10px] px-2 py-1 rounded-full font-black uppercase flex items-center gap-1">
          <Star size={12} />
          Recomendado
        </div>
      )}

      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className={`text-xl font-black uppercase italic leading-none mb-1 ${recomendada ? 'text-primary' : 'text-slate-900'}`}>
            {nombre}
          </h3>
          {ubicacion && (
            <div className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 font-medium">
              <MapPin size={12} />
              {ubicacion}
            </div>
          )}
        </div>
        <div className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-tight border ${statusColors[estado]}`}>
          {estado}
        </div>
      </div>

      <div className="flex items-end justify-between">
        <div>
          <p className="text-xs text-slate-400 font-bold uppercase mb-0.5">Desde</p>
          <p className={`text-2xl font-black ${recomendada ? 'text-slate-900' : 'text-slate-700'}`}>
            {precio}
          </p>
        </div>
        
        <button 
          className={`
            w-12 h-12 rounded-2xl flex items-center justify-center transition-all
            ${recomendada ? 'bg-primary text-white shadow-lg shadow-primary/30' : 'bg-slate-100 text-slate-400'}
          `}
        >
          <ArrowRight size={24} />
        </button>
      </div>

      {modo === 'completa' && (
        <div className="mt-4 pt-4 border-t border-slate-100 flex justify-between items-center text-xs">
          <div className="flex items-center gap-1.5 font-medium text-slate-600">
            <Info size={14} className="text-primary" />
            <span>Capacidad: {capacidad}</span>
          </div>
          {estado === 'critico' && (
            <div className="flex items-center gap-1 text-danger font-bold">
              <AlertCircle size={14} />
              <span>ALTA DEMANDA</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
