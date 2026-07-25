import { useMemo } from 'react';
import type { OperationalPhaseDTO, EventDayPhaseCreatePayload } from '../types';

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
  const sortedPhases = useMemo(
    () => [...phases].sort((a, b) => {
      const aOp = operationalPhases.find((p) => p.id === a.operational_phase_id);
      const bOp = operationalPhases.find((p) => p.id === b.operational_phase_id);
      return (aOp?.sort_order ?? 0) - (bOp?.sort_order ?? 0);
    }),
    [phases, operationalPhases],
  );

  const setTime = (index: number, field: 'start_min' | 'end_min', value: number | null) => {
    const originalIndex = phases.indexOf(sortedPhases[index]);
    if (originalIndex === -1) return;
    const updated = phases.map((p, i) => (i === originalIndex ? { ...p, [field]: value } : p));
    onChange(updated);
  };

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
              <th className="text-left py-2 pr-2 text-slate-500 font-medium">Nombre</th>
              <th className="text-left py-2 px-2 text-slate-500 font-medium">Orden</th>
              <th className="text-left py-2 px-2 text-slate-500 font-medium">Inicio</th>
              <th className="text-left py-2 pl-2 text-slate-500 font-medium">Fin</th>
            </tr>
          </thead>
          <tbody>
            {sortedPhases.map((phase, index) => {
              const op = operationalPhases.find((p) => p.id === phase.operational_phase_id);
              return (
                <tr key={phase.operational_phase_id} className="border-b border-slate-100">
                  <td className="py-2 pr-2 text-slate-800 font-medium">{op?.name ?? '—'}</td>
                  <td className="py-2 px-2 text-slate-500">{op?.sort_order ?? '—'}</td>
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
                  <td className="py-2 pl-2">
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
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {phases.length > 0 && operationalEndMin > operationalStartMin && (
        <div className="relative h-8 bg-slate-100 rounded-full overflow-hidden">
          {sortedPhases.map((phase, index) => {
            if (phase.start_min === null || phase.end_min === null) return null;
            const range = operationalEndMin - operationalStartMin;
            const left = ((phase.start_min - operationalStartMin) / range) * 100;
            const width = ((phase.end_min - phase.start_min) / range) * 100;
            const op = operationalPhases.find((p) => p.id === phase.operational_phase_id);
            const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500', 'bg-teal-500'];
            return (
              <div
                key={phase.operational_phase_id}
                className={`absolute top-0 h-full ${colors[index % colors.length]} opacity-60`}
                style={{ left: `${Math.max(0, left)}%`, width: `${Math.max(0, width)}%` }}
                title={op ? `${op.name}: ${minutesToTimeStr(phase.start_min)}-${minutesToTimeStr(phase.end_min)}` : ''}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
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
    if (p.start_min === null || p.end_min === null) {
      errors.push(`Fase #${i + 1}: debe completar inicio y fin`);
      continue;
    }
    if (p.start_min < operationalStartMin) {
      errors.push(`Fase #${i + 1}: el inicio (${minutesToTimeStr(p.start_min)}) es anterior al inicio de la jornada (${minutesToTimeStr(operationalStartMin)})`);
    }
    if (p.end_min > operationalEndMin) {
      errors.push(`Fase #${i + 1}: el fin (${minutesToTimeStr(p.end_min)}) supera el fin de la jornada (${minutesToTimeStr(operationalEndMin)})`);
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
    if (maxEnd < operationalEndMin) {
      errors.push('Las fases no cubren el fin de la jornada operativa');
    }
  }
  return errors;
}