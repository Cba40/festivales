import { Zone, SaturationLevel } from '../types';
import { useZoneMutations } from '../hooks/useZoneMutations';

interface Props {
  zone: Zone;
}

const saturationColors: Record<SaturationLevel, string> = {
  bajo: 'bg-green-100 text-green-800',
  medio: 'bg-yellow-100 text-yellow-800',
  alto: 'bg-orange-100 text-orange-800',
  colapsado: 'bg-red-100 text-red-800',
};

export function ZoneStatusCard({ zone }: Props) {
  const { updateSaturation, loading } = useZoneMutations();

  const handleSaturationChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    updateSaturation(zone.id, e.target.value as SaturationLevel);
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm border border-slate-200">
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="font-semibold text-slate-800">{zone.name}</h3>
          <p className="text-xs text-slate-500 capitalize">{zone.type}</p>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${saturationColors[zone.saturation]}`}>
          {zone.saturation}
        </span>
      </div>
      <div className="mt-4 flex justify-between items-end">
        <div className="text-sm">
          <p className="text-slate-600">Disp: <span className="font-semibold text-slate-800">{zone.availableCapacity}</span> / {zone.capacity}</p>
        </div>
        <select
          value={zone.saturation}
          onChange={handleSaturationChange}
          disabled={loading}
          className="text-sm border-slate-300 rounded-md py-1 px-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="bajo">Bajo</option>
          <option value="medio">Medio</option>
          <option value="alto">Alto</option>
          <option value="colapsado">Colapsado</option>
        </select>
      </div>
    </div>
  );
}
