import type { OperationalPhaseDTO, OperationalProfileDTO } from '../types';

interface OperationalPhaseListProps {
  phases: OperationalPhaseDTO[];
  profiles: OperationalProfileDTO[];
  onEdit: (phase: OperationalPhaseDTO) => void;
  onDelete: (id: string) => void;
}

function minutesToTimeStr(min: number): string {
  const h = Math.floor(min / 60).toString().padStart(2, '0');
  const m = (min % 60).toString().padStart(2, '0');
  return `${h}:${m}`;
}

export function OperationalPhaseList({ phases, profiles, onEdit, onDelete }: OperationalPhaseListProps) {
  if (phases.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        No hay fases definidas para este perfil. Creá la primera.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-slate-500">
            <th className="pb-2 font-medium">Perfil</th>
            <th className="pb-2 font-medium">Nombre</th>
            <th className="pb-2 font-medium">Inicio</th>
            <th className="pb-2 font-medium">Fin</th>
            <th className="pb-2 font-medium">Orden</th>
            <th className="pb-2 font-medium text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {phases.map((phase) => {
            const profile = profiles.find((p) => p.id === phase.operational_profile_id);
            return (
              <tr key={phase.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-3 text-slate-600">{profile?.name || '—'}</td>
                <td className="py-3 text-slate-800 font-medium">{phase.name}</td>
                <td className="py-3 text-slate-600">{minutesToTimeStr(phase.start_min)}</td>
                <td className="py-3 text-slate-600">
                    {phase.end_min > 1439
                      ? `${minutesToTimeStr(phase.end_min % 1440)} (+1)`
                      : minutesToTimeStr(phase.end_min)}
                  </td>
                <td className="py-3 text-slate-600">{phase.sort_order}</td>
                <td className="py-3 text-right">
                  <button
                    onClick={() => onEdit(phase)}
                    className="text-blue-600 hover:text-blue-800 mr-3 text-xs font-medium"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => onDelete(phase.id)}
                    className="text-red-600 hover:text-red-800 text-xs font-medium"
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
