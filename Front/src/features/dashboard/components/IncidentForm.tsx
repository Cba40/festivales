// src/features/dashboard/components/IncidentForm.tsx

import { useState } from 'react';
import { AlertTriangle, Send, Loader2, CheckCircle2 } from 'lucide-react';
import type { IncidentType, IncidentSeverity, ReportIncidentPayload } from '../types';
import { useIncidentMutations } from '../hooks/useIncidentMutations';

// ── Opciones del formulario ──

const INCIDENT_TYPES: { value: IncidentType; label: string; icon: string }[] = [
  { value: 'congestion', label: 'Congestión', icon: '🚗' },
  { value: 'closure', label: 'Cierre de zona', icon: '🚧' },
  { value: 'emergency', label: 'Emergencia', icon: '🚨' },
];

const SEVERITY_LEVELS: { value: IncidentSeverity; label: string; color: string }[] = [
  { value: 'baja', label: 'Baja', color: 'bg-emerald-500' },
  { value: 'media', label: 'Media', color: 'bg-amber-500' },
  { value: 'alta', label: 'Alta', color: 'bg-orange-500' },
  { value: 'critica', label: 'Crítica', color: 'bg-red-500' },
];

interface IncidentFormProps {
  onSuccess?: () => void;
}

export function IncidentForm({ onSuccess }: IncidentFormProps) {
  const { reportIncident, submitting, error } = useIncidentMutations();

  const [type, setType] = useState<IncidentType | ''>('');
  const [severity, setSeverity] = useState<IncidentSeverity | ''>('');
  const [description, setDescription] = useState('');
  const [submitted, setSubmitted] = useState(false);

  // Validación
  const isValid = type !== '' && severity !== '' && description.trim().length >= 5;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid || submitting) return;

    const payload: ReportIncidentPayload = {
      type: type as IncidentType,
      severity: severity as IncidentSeverity,
      description: description.trim(),
    };

    await reportIncident(payload);

    // Feedback + reset
    setSubmitted(true);
    setType('');
    setSeverity('');
    setDescription('');

    setTimeout(() => {
      setSubmitted(false);
      onSuccess?.();
    }, 1500);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Tipo de incidente */}
      <div>
        <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
          Tipo de incidente
        </label>
        <div className="grid grid-cols-3 gap-2">
          {INCIDENT_TYPES.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setType(opt.value)}
              className={`
                flex flex-col items-center gap-1.5 px-3 py-3 rounded-xl border-2 text-xs font-semibold
                transition-all duration-200 cursor-pointer
                ${type === opt.value
                  ? 'border-primary bg-primary/5 text-primary ring-2 ring-primary/20'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50'
                }
              `}
            >
              <span className="text-lg">{opt.icon}</span>
              <span>{opt.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Severidad */}
      <div>
        <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
          Severidad
        </label>
        <div className="flex gap-2">
          {SEVERITY_LEVELS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setSeverity(opt.value)}
              className={`
                flex items-center gap-2 px-4 py-2.5 rounded-xl border-2 text-xs font-semibold flex-1
                transition-all duration-200 cursor-pointer
                ${severity === opt.value
                  ? 'border-primary bg-primary/5 text-primary ring-2 ring-primary/20'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                }
              `}
            >
              <span className={`w-2.5 h-2.5 rounded-full ${opt.color}`} />
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Descripción */}
      <div>
        <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
          Descripción
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe el incidente con detalle suficiente para que el equipo pueda actuar..."
          rows={4}
          className="
            w-full px-4 py-3 rounded-xl border-2 border-slate-200 bg-white text-sm text-slate-800
            placeholder:text-slate-400
            focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20
            transition-all duration-200
            resize-none
          "
        />
        {description.length > 0 && description.trim().length < 5 && (
          <p className="mt-1 text-[11px] text-amber-600 flex items-center gap-1">
            <AlertTriangle size={12} />
            Mínimo 5 caracteres
          </p>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={!isValid || submitting}
        className={`
          w-full flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-2xl
          text-sm font-bold uppercase tracking-wide
          transition-all duration-300
          ${submitted
            ? 'bg-emerald-500 text-white'
            : isValid
              ? 'bg-primary text-white hover:bg-primary/90 shadow-lg shadow-primary/25 active:scale-[0.98] cursor-pointer'
              : 'bg-slate-200 text-slate-400 cursor-not-allowed'
          }
        `}
      >
        {submitted ? (
          <>
            <CheckCircle2 size={18} />
            ¡Incidente reportado!
          </>
        ) : submitting ? (
          <>
            <Loader2 size={18} className="animate-spin" />
            Enviando…
          </>
        ) : (
          <>
            <Send size={18} />
            Reportar incidente
          </>
        )}
      </button>
    </form>
  );
}
