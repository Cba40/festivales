import type { EventDaySummary } from '../types';

interface EventDayListProps {
  eventDays: EventDaySummary[];
  onEdit: (day: EventDaySummary) => void;
  onDelete: (id: string) => void;
}

const weatherLabels: Record<string, string> = {
  soleado: '☀️ Soleado',
  nublado: '☁️ Nublado',
  lluvioso: '🌧️ Lluvioso',
  tormenta: '⛈️ Tormenta',
};

export function EventDayList({ eventDays, onEdit, onDelete }: EventDayListProps) {
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
            <th className="pb-2 font-medium">Fecha</th>
            <th className="pb-2 font-medium">Día</th>
            <th className="pb-2 font-medium">Clima</th>
            <th className="pb-2 font-medium">Artista</th>
            <th className="pb-2 font-medium">Convocatoria</th>
            <th className="pb-2 font-medium">Activo</th>
            <th className="pb-2 font-medium text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {eventDays.map((day) => (
            <tr key={day.id} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="py-3 text-slate-800">{day.date}</td>
              <td className="py-3 text-slate-600 capitalize">{day.day_of_week}</td>
              <td className="py-3 text-slate-600">
                {day.weather ? (weatherLabels[day.weather] ?? day.weather) : '—'}
              </td>
              <td className="py-3 text-slate-600">{day.headliner_artist || '—'}</td>
              <td className="py-3 text-slate-600">
                {day.estimated_attendance
                  ? day.estimated_attendance.toLocaleString()
                  : '—'}
              </td>
              <td className="py-3">
                <span
                  className={`inline-block w-2 h-2 rounded-full ${
                    day.is_active ? 'bg-green-500' : 'bg-slate-300'
                  }`}
                />
              </td>
              <td className="py-3 text-right">
                <button
                  onClick={() => onEdit(day)}
                  className="text-blue-600 hover:text-blue-800 mr-3 text-xs font-medium"
                >
                  Editar
                </button>
                <button
                  onClick={() => onDelete(day.id)}
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
