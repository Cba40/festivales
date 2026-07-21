import type { AttendanceLevelDTO } from '../types';

interface AttendanceLevelListProps {
  levels: AttendanceLevelDTO[];
  onEdit: (level: AttendanceLevelDTO) => void;
  onDelete: (id: string) => void;
}

export function AttendanceLevelList({ levels, onEdit, onDelete }: AttendanceLevelListProps) {
  if (levels.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        No hay niveles de asistencia. Creá el primero.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-slate-500">
            <th className="pb-2 font-medium">Nombre</th>
            <th className="pb-2 font-medium">Mínimo</th>
            <th className="pb-2 font-medium">Máximo</th>
            <th className="pb-2 font-medium">Multiplicador</th>
            <th className="pb-2 font-medium text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {levels.map((level) => (
            <tr key={level.id} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="py-3 text-slate-800 font-medium">{level.name}</td>
              <td className="py-3 text-slate-600">{level.min_people.toLocaleString()}</td>
              <td className="py-3 text-slate-600">
                {level.max_people !== null ? level.max_people.toLocaleString() : '—'}
              </td>
              <td className="py-3 text-slate-600">{level.global_multiplier.toFixed(2)}</td>
              <td className="py-3 text-right">
                <button
                  onClick={() => onEdit(level)}
                  className="text-blue-600 hover:text-blue-800 mr-3 text-xs font-medium"
                >
                  Editar
                </button>
                <button
                  onClick={() => onDelete(level.id)}
                  className="text-red-600 hover:text-red-800 text-xs font-medium"
                >
                  Eliminar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
