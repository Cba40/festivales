import type { EventDaySummary, ServiceConfigDTO, ZoneTypeDTO } from '../types';

interface ServiceConfigListProps {
  configs: ServiceConfigDTO[];
  zoneTypes: ZoneTypeDTO[];
  eventDays: EventDaySummary[];
  onEdit: (config: ServiceConfigDTO) => void;
  onDelete: (id: string) => void;
}

export function ServiceConfigList({
  configs,
  zoneTypes,
  eventDays,
  onEdit,
  onDelete,
}: ServiceConfigListProps) {
  const zoneTypeName = (id: string) =>
    zoneTypes.find((zt) => zt.id === id)?.name ?? id;

  const eventDayDate = (id: string) => {
    const day = eventDays.find((d) => d.id === id);
    return day ? day.date : id;
  };

  if (configs.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        No hay configuraciones de servicios. Creá la primera.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-slate-500">
            <th className="pb-2 font-medium">Tipo de zona</th>
            <th className="pb-2 font-medium">Subtipo</th>
            <th className="pb-2 font-medium">Jornada</th>
            <th className="pb-2 font-medium">Permanencia</th>
            <th className="pb-2 font-medium text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {configs.map((config) => (
            <tr key={config.id} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="py-3 text-slate-800 font-medium">
                {zoneTypeName(config.zone_type_id)}
              </td>
              <td className="py-3 text-slate-600">{config.subtipo || '—'}</td>
              <td className="py-3">
                {config.event_day_id ? (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                    Override: {eventDayDate(config.event_day_id)}
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
                    Default
                  </span>
                )}
              </td>
              <td className="py-3 text-slate-600">{config.average_duration_min} min</td>
              <td className="py-3 text-right">
                <button
                  onClick={() => onEdit(config)}
                  className="text-blue-600 hover:text-blue-800 mr-3 text-xs font-medium"
                >
                  Editar
                </button>
                <button
                  onClick={() => onDelete(config.id)}
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