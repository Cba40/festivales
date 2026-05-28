import { useState } from 'react';
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

  const handleDelete = async (id: string) => {
    await deleteZone(id);
  };

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

      <div className="space-y-3">
        {zones.map((zone) => (
          <div
            key={zone.id}
            className="bg-white p-4 rounded-lg border border-slate-200 flex items-center justify-between"
          >
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-slate-800 truncate">{zone.name}</h3>
              <div className="flex gap-3 mt-1 text-sm text-slate-500">
                <span className="capitalize">{zone.type}</span>
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
                className="p-2 text-sm text-red-600 hover:bg-red-50 rounded-md transition-colors"
                title="Eliminar zona"
              >
                🗑️
              </button>
            </div>
          </div>
        ))}

        {zones.length === 0 && (
          <p className="text-sm text-slate-500 italic text-center py-8">
            No hay zonas registradas. Crea la primera usando el botón "+ Nueva Zona".
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
