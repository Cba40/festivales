import { Edit, Trash2 } from 'lucide-react';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import type { EventDaySummary } from '../types';

interface EventDayListProps {
  eventDays: EventDaySummary[];
  onEdit: (day: EventDaySummary) => void;
  onRequestDelete: (id: string) => void;
}

const weatherLabels: Record<string, string> = {
  soleado: '☀️ Soleado',
  nublado: '☁️ Nublado',
  lluvioso: '🌧️ Lluvioso',
  tormenta: '⛈️ Tormenta',
};

const dateFormatter = new Intl.DateTimeFormat('es-AR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  timeZone: 'UTC',
});

function formatDate(date: string): string {
  const parsed = new Date(date);
  return Number.isNaN(parsed.getTime()) ? date : dateFormatter.format(parsed);
}

export function EventDayList({ eventDays, onEdit, onRequestDelete }: EventDayListProps) {
  if (eventDays.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        No hay días cargados para este evento.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-slate-500">
            <th className="pb-2 pr-2 font-medium">Fecha</th>
            <th className="pb-2 pr-2 font-medium">Día</th>
            <th className="pb-2 pr-2 font-medium">Clima</th>
            <th className="pb-2 pr-2 font-medium">Artista</th>
            <th className="pb-2 pr-2 font-medium">Activo</th>
            <th className="pb-2 font-medium text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {eventDays.map((day) => (
            <tr key={day.id} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="py-3 pr-2 text-slate-800 whitespace-nowrap">{formatDate(day.date)}</td>
              <td className="py-3 pr-2 text-slate-600 capitalize">{day.day_of_week}</td>
              <td className="py-3 pr-2 text-slate-600">
                {day.weather ? (weatherLabels[day.weather] ?? day.weather) : '—'}
              </td>
              <td className="py-3 pr-2 text-slate-600">{day.headliner_artist || '—'}</td>
              <td className="py-3 pr-2">
                {day.is_active ? (
                  <Badge variant="success">Activo</Badge>
                ) : (
                  <Badge variant="neutral">Inactivo</Badge>
                )}
              </td>
              <td className="py-3 text-right whitespace-nowrap">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onEdit(day)}
                  title="Editar"
                  className="mr-1"
                >
                  <Edit className="w-3.5 h-3.5" />
                  Editar
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onRequestDelete(day.id)}
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