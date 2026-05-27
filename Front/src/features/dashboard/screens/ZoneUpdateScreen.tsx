import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../../../core/state/store';
import { ZoneStatusCard } from '../components/ZoneStatusCard';

export function ZoneUpdateScreen() {
  const navigate = useNavigate();
  const zones = useAppStore((state) => state.zones);
  const [filter, setFilter] = useState<string>('all');

  const filteredZones = filter === 'all' ? zones : zones.filter(z => z.type === filter);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-4">
        <button 
          onClick={() => navigate('/dashboard')}
          className="text-slate-500 hover:text-slate-800"
        >
          &larr; Volver
        </button>
        <h1 className="text-xl font-bold text-slate-800">Actualización de Zonas</h1>
      </header>

      <main className="p-6 max-w-4xl mx-auto">
        <div className="mb-6">
          <label className="text-sm font-medium text-slate-700 mr-3">Filtrar por tipo:</label>
          <select 
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="border-slate-300 rounded-md py-1 px-3 text-sm focus:ring-blue-500"
          >
            <option value="all">Todas</option>
            <option value="estacionamiento">Estacionamiento</option>
            <option value="transporte">Transporte</option>
            <option value="comida">Comida</option>
            <option value="servicios">Servicios</option>
          </select>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredZones.map(zone => (
            <ZoneStatusCard key={zone.id} zone={zone} />
          ))}
        </div>
      </main>
    </div>
  );
}
