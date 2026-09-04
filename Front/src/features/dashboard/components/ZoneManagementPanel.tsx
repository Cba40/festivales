import { useState, useMemo } from 'react';
import { useAppStore } from '../../../core/state/store';
import { useZoneConfigMutations } from '../hooks/useZoneConfigMutations';
import { CreateZoneForm } from './CreateZoneForm';
import { ZoneConfigModal } from './ZoneConfigModal';
import type { Zone } from '../types';

export function ZoneManagementPanel() {
  const zones = useAppStore((state) => state.zones);
  const { deleteZone, loading } = useZoneConfigMutations();
  const [showCreate, setShowCreate] = useState(false);
  const [editingZone, setEditingZone] = useState<Zone | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const handleDelete = async (id: string) => {
    await deleteZone(id);
  };

  // Filtrar y agrupar zonas por categoría (type + subtipo)
  const groupedZones = useMemo(() => {
    const filtered = zones.filter((zone) => {
      const term = searchTerm.toLowerCase();
      return (
        zone.name.toLowerCase().includes(term) ||
        zone.type.toLowerCase().includes(term) ||
        (zone.subtipo && zone.subtipo.toLowerCase().includes(term))
      );
    });

    const grouped: Record<string, Zone[]> = {};
    filtered.forEach((zone) => {
      const category = zone.subtipo 
        ? `${zone.type} (${zone.subtipo})` 
        : zone.type;
      
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(zone);
    });

    // Ordenar categorías alfabéticamente
    return Object.keys(grouped)
      .sort()
      .reduce((acc, key) => {
        acc[key] = grouped[key];
        return acc;
      }, {} as Record<string, Zone[]>);
  }, [zones, searchTerm]);

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold text-slate-700">
          Zonas Registradas ({zones.length})
        </h2>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md text-sm font-medium transition-colors"
        >
          + Nueva Zona
        </button>
      </div>

      {showCreate && (
        <div className="mb-6">
          <CreateZoneForm
            onSuccess={() => setShowCreate(false)}
            onCancel={() => setShowCreate(false)}
          />
        </div>
      )}

      {/* Buscador */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Buscar por nombre, tipo o subtipo..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-4 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm bg-white"
        />
      </div>

      <div className="space-y-6">
        {Object.entries(groupedZones).map(([category, categoryZones]) => (
          <div key={category}>
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3 border-b border-slate-200 pb-1">
              {category} ({categoryZones.length})
            </h3>
            <div className="space-y-3">
              {categoryZones.map((zone) => (
                <div
                  key={zone.id}
                  className="bg-white p-4 rounded-lg border border-slate-200 flex items-center justify-between hover:border-blue-300 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-slate-800 truncate">{zone.name}</h4>
                    <div className="flex gap-3 mt-1 text-sm text-slate-500">
                      <span>Cap: {zone.capacity}</span>
                      {zone.lat !== undefined && (
                        <span className="text-slate-400">
                          {zone.lat.toFixed(4)}, {zone.lng?.toFixed(4)}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2 ml-4 shrink-0">
                    <button
                      onClick={() => setEditingZone(zone)}
                      className="p-2 text-sm text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
                      title="Editar configuración"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => handleDelete(zone.id)}
                      disabled={loading}
                      className="p-2 text-sm text-red-600 hover:bg-red-50 rounded-md transition-colors disabled:opacity-50"
                      title="Eliminar zona"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
        
        {Object.keys(groupedZones).length === 0 && (
          <p className="text-sm text-slate-500 italic text-center py-8 bg-slate-50 rounded-lg border border-dashed border-slate-300">
            {searchTerm 
              ? 'No se encontraron zonas que coincidan con la búsqueda.' 
              : 'No hay zonas registradas. Crea la primera usando el botón "+ Nueva Zona".'}
          </p>
        )}
      </div>

      {editingZone && (
        <ZoneConfigModal
          zone={editingZone}
          onClose={() => setEditingZone(null)}
        />
      )}
    </div>
  );
}
