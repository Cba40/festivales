import type { OperationalProfileDTO } from '../types';

interface OperationalProfileListProps {
  profiles: OperationalProfileDTO[];
  onEdit: (profile: OperationalProfileDTO) => void;
  onDelete: (id: string) => void;
}

export function OperationalProfileList({ profiles, onEdit, onDelete }: OperationalProfileListProps) {
  if (profiles.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        No hay perfiles operativos. Creá el primero.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-slate-500">
            <th className="pb-2 font-medium">Nombre</th>
            <th className="pb-2 font-medium">Descripción</th>
            <th className="pb-2 font-medium text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {profiles.map((profile) => (
            <tr key={profile.id} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="py-3 text-slate-800 font-medium">{profile.name}</td>
              <td className="py-3 text-slate-600 max-w-xs truncate">
                {profile.description || '—'}
              </td>
              <td className="py-3 text-right">
                <button
                  onClick={() => onEdit(profile)}
                  className="text-blue-600 hover:text-blue-800 mr-3 text-xs font-medium"
                >
                  Editar
                </button>
                <button
                  onClick={() => onDelete(profile.id)}
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
