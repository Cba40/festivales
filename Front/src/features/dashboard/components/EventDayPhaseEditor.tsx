import { useState, useCallback } from 'react';
import type { OperationalPhaseDTO, EventDayPhaseCreatePayload } from '../types';
import { minutesToTimeStr, timeStrToMinutes } from '../utils/operationalMinutes';

function insertSorted(
  phases: EventDayPhaseCreatePayload[],
  newPhase: EventDayPhaseCreatePayload,
  operationalPhases: OperationalPhaseDTO[],
): EventDayPhaseCreatePayload[] {
  const sorted = [...phases, newPhase].sort((a, b) => {
    const aOp = operationalPhases.find((p) => p.id === a.operational_phase_id);
    const bOp = operationalPhases.find((p) => p.id === b.operational_phase_id);
    return (aOp?.sort_order ?? 0) - (bOp?.sort_order ?? 0);
  });
  return sorted;
}

interface EventDayPhaseEditorProps {
  phases: EventDayPhaseCreatePayload[];
  operationalPhases: OperationalPhaseDTO[];
  onChange: (phases: EventDayPhaseCreatePayload[]) => void;
  errors: string[];
}

export function EventDayPhaseEditor({
  phases, operationalPhases, onChange, errors,
}: EventDayPhaseEditorProps) {
  const [showAddSelector, setShowAddSelector] = useState(false);

  const addPhase = useCallback((opId: string) => {
    onChange(insertSorted(phases, { operational_phase_id: opId, start_min: null, end_min: null, intensity: 1 }, operationalPhases));
    setShowAddSelector(false);
  }, [phases, onChange, operationalPhases]);

  const setTime = useCallback((index: number, field: 'start_min' | 'end_min', value: number | null) => {
    onChange(phases.map((p, i) => (i === index ? { ...p, [field]: value } : p)));
  }, [phases, onChange]);

  const setIntensity = useCallback((index: number, value: number) => {
    onChange(phases.map((p, i) => (i === index ? { ...p, intensity: value } : p)));
  }, [phases, onChange]);

  const deletePhase = useCallback((index: number) => {
    onChange(phases.filter((_, i) => i !== index));
  }, [phases, onChange]);

  const duplicatePhase = useCallback((index: number) => {
    const copy: EventDayPhaseCreatePayload = { ...phases[index] };
    onChange(insertSorted(phases, copy, operationalPhases));
  }, [phases, onChange, operationalPhases]);

  const changeBehavior = useCallback((index: number, newOpId: string) => {
    onChange(phases.map((p, i) => (i === index ? { ...p, operational_phase_id: newOpId } : p)));
  }, [phases, onChange]);

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-slate-700">Fases de la jornada</h3>

      {errors.length > 0 && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 space-y-1">
          {errors.map((err, i) => <p key={i}>{err}</p>)}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-2 pr-2 text-slate-500 font-medium">Comportamiento</th>
              <th className="text-left py-2 px-2 text-slate-500 font-medium">Inicio</th>
              <th className="text-left py-2 px-2 text-slate-500 font-medium">Fin</th>
              <th className="text-left py-2 px-2 text-slate-500 font-medium">Intensidad</th>
              <th className="text-right py-2 pl-2 text-slate-500 font-medium">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {phases.map((phase, index) => {
              const op = operationalPhases.find((p) => p.id === phase.operational_phase_id);
              return (
                <tr key={index} className="border-b border-slate-100">
                  <td className="py-2 pr-2">
                    <select
                      value={phase.operational_phase_id}
                      onChange={(e) => changeBehavior(index, e.target.value)}
                      className="w-full px-2 py-1 border border-slate-300 rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {operationalPhases.map((op) => (
                        <option key={op.id} value={op.id}>{op.name}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2 px-2">
                    <input
                      type="time"
                      value={phase.start_min !== null ? minutesToTimeStr(phase.start_min) : ''}
                      onChange={(e) => {
                        const val = e.target.value;
                        setTime(index, 'start_min', val ? timeStrToMinutes(val) : null);
                      }}
                      className="w-28 px-2 py-1 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </td>
                  <td className="py-2 px-2">
                    <input
                      type="time"
                      value={phase.end_min !== null ? minutesToTimeStr(phase.end_min) : ''}
                      onChange={(e) => {
                        const val = e.target.value;
                        setTime(index, 'end_min', val ? timeStrToMinutes(val) : null);
                      }}
                      className="w-28 px-2 py-1 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </td>
                  <td className="py-2 px-2">
                    <input
                      type="number"
                      min={0.1}
                      step={0.1}
                      value={phase.intensity}
                      onChange={(e) => {
                        const val = Number(e.target.value);
                        if (Number.isFinite(val) && val > 0) setIntensity(index, val);
                      }}
                      className="w-20 px-2 py-1 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </td>
                  <td className="py-2 pl-2 text-right whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => duplicatePhase(index)}
                      className="px-1.5 py-1 text-xs text-slate-500 hover:text-blue-600 transition-colors"
                      title="Duplicar"
                    >Duplicar</button>
                    <button
                      type="button"
                      onClick={() => deletePhase(index)}
                      className="px-1.5 py-1 text-xs text-red-500 hover:text-red-700 transition-colors"
                      title="Eliminar"
                    >Eliminar</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-2">
        {showAddSelector ? (
          <select
            defaultValue=""
            onChange={(e) => {
              if (e.target.value) addPhase(e.target.value);
            }}
            onBlur={() => setShowAddSelector(false)}
            autoFocus
            className="px-3 py-1.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="" disabled>Seleccionar fase...</option>
            {operationalPhases.map((op) => (
              <option key={op.id} value={op.id}>{op.name}</option>
            ))}
          </select>
        ) : (
          <button
            type="button"
            onClick={() => setShowAddSelector(true)}
            className="px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
          >
            + Agregar fase
          </button>
        )}
      </div>
    </div>
  );
}

export function validatePhases(
  phases: EventDayPhaseCreatePayload[],
  operationalStartMin: number,
  resolvedOperationalEndMin: number,
): string[] {
  const errors: string[] = [];
  if (phases.length === 0) {
    errors.push('Debe haber al menos una fase en la jornada');
    return errors;
  }

  for (let i = 0; i < phases.length; i++) {
    const p = phases[i];
    if (p.start_min === null || p.end_min === null) {
      errors.push(`Fase #${i + 1}: debe completar inicio y fin`);
      continue;
    }
    if (p.start_min < operationalStartMin) {
      errors.push(`Fase #${i + 1}: el inicio (${minutesToTimeStr(p.start_min)}) es anterior al inicio de la jornada (${minutesToTimeStr(operationalStartMin)})`);
    }
    if (p.end_min > resolvedOperationalEndMin) {
      errors.push(`Fase #${i + 1}: el fin (${minutesToTimeStr(p.end_min)}) supera el fin de la jornada (${minutesToTimeStr(resolvedOperationalEndMin)})`);
    }
    if (p.end_min <= p.start_min) {
      errors.push(`Fase #${i + 1}: el fin debe ser posterior al inicio`);
    }
    for (let j = i + 1; j < phases.length; j++) {
      const q = phases[j];
      if (q.start_min === null || q.end_min === null) continue;
      if (p.start_min < q.end_min && q.start_min < p.end_min) {
        errors.push(`Las fases #${i + 1} y #${j + 1} se superponen`);
      }
    }
  }

  const nonNull = phases.filter((p) => p.start_min !== null && p.end_min !== null);
  if (nonNull.length > 0) {
    const allStart = nonNull.map((p) => p.start_min as number);
    const allEnd = nonNull.map((p) => p.end_min as number);
    const minStart = Math.min(...allStart);
    const maxEnd = Math.max(...allEnd);
    if (minStart > operationalStartMin) {
      errors.push('Las fases no cubren el inicio de la jornada operativa');
    }
    if (maxEnd < resolvedOperationalEndMin) {
      errors.push('Las fases no cubren el fin de la jornada operativa');
    }
  }
  return errors;
}
