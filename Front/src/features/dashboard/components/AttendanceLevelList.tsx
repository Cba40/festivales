import { Edit, Trash2 } from 'lucide-react';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import type { AttendanceLevelDTO } from '../types';

interface AttendanceLevelListProps {
  levels: AttendanceLevelDTO[];
  onEdit: (level: AttendanceLevelDTO) => void;
  onRequestDelete: (id: string) => void;
}

export function AttendanceLevelList({ levels, onEdit, onRequestDelete }: AttendanceLevelListProps) {
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
            <th className="pb-2 pr-2 font-medium">Nombre</th>
            <th className="pb-2 pr-2 font-medium">Mínimo</th>
            <th className="pb-2 pr-2 font-medium">Máximo</th>
            <th className="pb-2 pr-2 font-medium">Estado</th>
            <th className="pb-2 font-medium text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {levels.map((level) => (
            <tr key={level.id} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="py-3 pr-2 text-slate-800 font-medium">{level.name}</td>
              <td className="py-3 pr-2 text-slate-600">{level.min_people.toLocaleString()}</td>
              <td className="py-3 pr-2 text-slate-600">
                {level.max_people !== null ? level.max_people.toLocaleString() : '—'}
              </td>
              <td className="py-3 pr-2">
                {level.max_people !== null ? (
                  <Badge variant="info">Acotado</Badge>
                ) : (
                  <Badge variant="neutral">Sin límite</Badge>
                )}
              </td>
              <td className="py-3 text-right whitespace-nowrap">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onEdit(level)}
                  title="Editar"
                  className="mr-1"
                >
                  <Edit className="w-3.5 h-3.5" />
                  Editar
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onRequestDelete(level.id)}
                  title="Eliminar"
                  className="text-red-600 hover:bg-red-50"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Eliminar
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}