import { useState, useEffect } from 'react';
import type { OperationalPhaseDTO, EventDayPhaseDTO, EventDayPhaseCreatePayload } from '../types';

interface EventDayPhaseEditorProps {
  phases: EventDayPhaseCreatePayload[];
  operationalPhases: OperationalPhaseDTO[];
  operationalStartMin: number;
  operationalEndMin: number;
  onChange: (phases: EventDayPhaseCreatePayload[]) => void;
  errors: string[];
}

function minutesToTimeStr(min: number): string {
  const h = Math.floor(min / 60).toString().padStart(2, '0');
  const m = (min % 60).toString().padStart(2, '0');
  return `${h}:${m}`;
}

function timeStrToMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number);
  return h * 60 + m;
}

export function EventDayPhaseEditor({
  phases, operationalPhases, operationalStartMin, operationalEndMin, onChange, errors,
}: EventDayPhaseEditorProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [dirtySet, setDirtySet] = useState<Set<number>>(new Set());

  useEffect(() => {
    let changed = false;
    const fixed = phases.map((p) => {
      if (p.end_min > 1439) {
        const raw = p.end_min % 1440;
        if (raw >= p.start_min) {
          changed = true;
          return { ...p, end_min: raw };
        }
      }
      return p;
    });
    if (changed) {
      onChange(fixed);
    }
  }, [phases]);

  const phaseOptions = operationalPhases.filter(
    (op) => !phases.some((p) => p.operational_phase_id === op.id),
  );

  const addNew = () => {
    const template = operationalPhases.length > 0 ? operationalPhases[0] : null;
    onChange([
      ...phases,
      {
        operational_phase_id: template ? template.id : '',
        start_min: template ? template.start_min : operationalStartMin,
        end_min: template ? template.end_min : operationalEndMin,
      },
    ]);
    setEditingIndex(phases.length);
  };

  const updatePhase = (index: number, field: keyof EventDayPhaseCreatePayload, value: unknown) => {
    const updated = phases.map((p, i) => (i === index ? { ...p, [field]: value } : p));
    onChange(updated);
  };

  const handlePhaseSelect = (index: number, phaseId: string) => {
    const updated = phases.map((p, i) => {
      if (i !== index) return p;
      const next = { ...p, operational_phase_id: phaseId };
      if (!dirtySet.has(index)) {
        const op = operationalPhases.find(o => o.id === phaseId);
        if (op) {
          next.start_min = op.start_min;
          next.end_min = op.end_min;
        }
      }
      return next;
    });
    onChange(updated);
  };

  const handleTimeEdit = (index: number, field: 'start_min' | 'end_min', value: number) => {
    if (!dirtySet.has(index)) {
      setDirtySet(prev => new Set(prev).add(index));
    }
    updatePhase(index, field, value);
  };

  const removePhase = (index: number) => {
    onChange(phases.filter((_, i) => i !== index));
    setDirtySet(prev => {
      const next = new Set<number>();
      for (const idx of prev) {
        if (idx < index) next.add(idx);
        else if (idx > index) next.add(idx - 1);
      }
      return next;
    });
    if (editingIndex === index) setEditingIndex(null);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">Fases de la jornada</h3>
        <button
          type="button"
          onClick={addNew}
          disabled={phaseOptions.length === 0}
          className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          + Agregar fase
        </button>
      </div>

      {errors.length > 0 && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 space-y-1">
          {errors.map((err, i) => <p key={i}>{err}</p>)}
        </div>
      )}

      {phases.length === 0 && !editingIndex && (
        <div className="text-xs text-slate-400 py-4 text-center border border-dashed border-slate-300 rounded-lg">
          No hay fases definidas. Agregá al menos una fase para la jornada.
        </div>
      )}

      <div className="space-y-2">
        {phases.map((phase, index) => {
          const op = operationalPhases.find((p) => p.id === phase.operational_phase_id);
          const isEditing = editingIndex === index;
          return (
            <div
              key={index}
              className={`p-3 rounded-lg border transition-colors ${
                isEditing ? 'border-blue-300 bg-blue-50' : 'border-slate-200 bg-white'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="flex-1 grid grid-cols-1 sm:grid-cols-4 gap-2">
                  <div>
                    <label className="text-[10px] text-slate-400 block mb-0.5">Fase operativa</label>
                    <select
                      value={phase.operational_phase_id}
                      onChange={(e) => handlePhaseSelect(index, e.target.value)}
                      className="w-full px-2 py-1.5 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Seleccionar...</option>
                      {operationalPhases.map((op2) => (
                        <option key={op2.id} value={op2.id}>{op2.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 block mb-0.5">Inicio</label>
                    <input
                      type="time"
                      value={minutesToTimeStr(phase.start_min)}
                      onChange={(e) => handleTimeEdit(index, 'start_min', timeStrToMinutes(e.target.value))}
                      className="w-full px-2 py-1.5 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 block mb-0.5">Fin</label>
                    <input
                      type="time"
                      value={minutesToTimeStr(phase.end_min > 1439 ? phase.end_min % 1440 : phase.end_min)}
                      onChange={(e) => {
                        const raw = timeStrToMinutes(e.target.value);
                        handleTimeEdit(index, 'end_min', raw + (phase.end_min > 1439 ? 1440 : 0));
                      }}
                      className="w-full px-2 py-1.5 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <label className="flex items-center gap-1.5 mt-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={phase.end_min > 1439}
                      onChange={() => {
                        const raw = phase.end_min > 1439 ? phase.end_min % 1440 : phase.end_min;
                        handleTimeEdit(index, 'end_min', phase.end_min > 1439 ? raw : raw + 1440);
                      }}
                        disabled={phase.end_min > 1439 ? (phase.end_min % 1440) >= phase.start_min : (phase.end_min) >= phase.start_min}
                        className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                      />
                      <span className="text-[10px] text-slate-500">Finaliza al día siguiente</span>
                    </label>
                  </div>
                  <div className="flex items-end gap-1">
                    <button
                      type="button"
                      onClick={() => setEditingIndex(isEditing ? null : index)}
                      className="px-2 py-1.5 text-xs text-blue-600 hover:text-blue-800 border border-blue-200 rounded-md hover:bg-blue-50 transition-colors"
                    >
                      {isEditing ? 'OK' : 'Editar'}
                    </button>
                    <button
                      type="button"
                      onClick={() => removePhase(index)}
                      className="px-2 py-1.5 text-xs text-red-600 hover:text-red-800 border border-red-200 rounded-md hover:bg-red-50 transition-colors"
                    >
                      Eliminar
                    </button>
                  </div>
                </div>
              </div>
              {op && (
                <div className="mt-1.5 text-[10px] text-slate-400">
                  {op.name}: {minutesToTimeStr(phase.start_min)} — {minutesToTimeStr(phase.end_min > 1439 ? phase.end_min % 1440 : phase.end_min)}
                  {op.sort_order !== undefined && ` (orden ${op.sort_order})`}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {phases.length > 0 && operationalEndMin > operationalStartMin && (
        <div className="relative h-8 bg-slate-100 rounded-full overflow-hidden">
          {phases.map((phase, index) => {
            const range = operationalEndMin - operationalStartMin;
            const left = ((phase.start_min - operationalStartMin) / range) * 100;
            const width = ((phase.end_min - phase.start_min) / range) * 100;
            const op = operationalPhases.find((p) => p.id === phase.operational_phase_id);
            const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500', 'bg-teal-500'];
            return (
              <div
                key={index}
                className={`absolute top-0 h-full ${colors[index % colors.length]} opacity-60`}
                style={{ left: `${Math.max(0, left)}%`, width: `${Math.max(0, width)}%` }}
                title={op ? `${op.name}: ${minutesToTimeStr(phase.start_min)}-${minutesToTimeStr(phase.end_min > 1439 ? phase.end_min % 1440 : phase.end_min)}` : ''}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

export function validatePhases(
  phases: EventDayPhaseCreatePayload[],
  operationalStartMin: number,
  operationalEndMin: number,
): string[] {
  const errors: string[] = [];
  if (phases.length === 0) {
    errors.push('Debe haber al menos una fase en la jornada');
    return errors;
  }
  for (let i = 0; i < phases.length; i++) {
    const p = phases[i];
    if (!p.operational_phase_id) {
      errors.push(`Fase #${i + 1}: debe seleccionar una fase operativa`);
      continue;
    }
    if (p.start_min < operationalStartMin) {
      errors.push(`Fase #${i + 1}: el inicio (${p.start_min}) es anterior al inicio de la jornada (${operationalStartMin})`);
    }
    if (p.end_min > operationalEndMin) {
      errors.push(`Fase #${i + 1}: el fin (${p.end_min}) supera el fin de la jornada (${operationalEndMin})`);
    }
    if (p.end_min <= p.start_min) {
      errors.push(`Fase #${i + 1}: el fin debe ser posterior al inicio`);
    }
    for (let j = i + 1; j < phases.length; j++) {
      const q = phases[j];
      if (p.start_min < q.end_min && q.start_min < p.end_min) {
        errors.push(`Las fases #${i + 1} y #${j + 1} se superponen`);
      }
    }
  }
  const allStart = phases.map((p) => p.start_min);
  const allEnd = phases.map((p) => p.end_min);
  const minStart = Math.min(...allStart);
  const maxEnd = Math.max(...allEnd);
  if (minStart > operationalStartMin) {
    errors.push('Las fases no cubren el inicio de la jornada operativa');
  }
  if (maxEnd < operationalEndMin) {
    errors.push('Las fases no cubren el fin de la jornada operativa');
  }
  return errors;
}