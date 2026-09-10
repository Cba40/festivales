import { useState } from 'react';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { useAppStore } from '../../../core/state/store';
import { useZoneConfigMutations } from '../hooks/useZoneConfigMutations';
import { CreateZoneForm } from './CreateZoneForm';
import { ZoneConfigModal } from './ZoneConfigModal';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { ConfirmDialog } from './ui/ConfirmDialog';
import type { Zone } from '../types';

const TYPE_LABELS: Record<string, string> = {
  estacionamiento: 'Estacionamiento',
  transporte: 'Transporte',
  comida: 'Comida',
  servicios: 'Servicios',
  salida: 'Salida',
};

function formatLocation(zone: Zone): string {
  if (zone.lat === undefined || zone.lng === undefined) return '—';
  return `${zone.lat.toFixed(2)}, ${zone.lng.toFixed(2)}`;
}

export function ZoneManagementPanel() {
  const zones = useAppStore((state) => state.zones);
  const { deleteZone, loading, error } = useZoneConfigMutations();
  const [showCreate, setShowCreate] = useState(false);
  const [editingZone, setEditingZone] = useState<Zone | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  const handleDeleteConfirm = async (id: string) => {
    setPendingDeleteId(null);
    await deleteZone(id);
  };

  return (
    <div className="space-y-6">
      <Card variant="standard">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-4">
          <h2 className="text-lg font-semibold text-slate-800">
            Zonas Registradas ({zones.length})
          </h2>
          {!showCreate && (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="w-4 h-4" />
              Nueva Zona
            </Button>
          )}
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="pb-2 pr-2 font-medium">Nombre</th>
                <th className="pb-2 pr-2 font-medium">Tipo</th>
                <th className="pb-2 pr-2 font-medium">Capacidad</th>
                <th className="pb-2 pr-2 font-medium">Ubicación</th>
                <th className="pb-2 font-medium text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {zones.map((zone) => (
                <tr key={zone.id} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="py-3 pr-2 text-slate-800 font-medium">{zone.name}</td>
                  <td className="py-3 pr-2">
                    <Badge variant="neutral">
                      {TYPE_LABELS[zone.type] ?? zone.type}
                    </Badge>
                  </td>
                  <td className="py-3 pr-2 text-slate-600">{zone.capacity.toLocaleString('es-AR')}</td>
                  <td className="py-3 pr-2 text-slate-400 whitespace-nowrap">{formatLocation(zone)}</td>
                  <td className="py-3 text-right whitespace-nowrap">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditingZone(zone)}
                      title="Editar configuración"
                      className="mr-1"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                      Editar
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setPendingDeleteId(zone.id)}
                      disabled={loading}
                      title="Eliminar zona"
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

        {zones.length === 0 && (
          <p className="text-sm text-slate-500 italic text-center py-8">
            No hay zonas registradas. Crea la primera usando el botón "+ Nueva Zona".
          </p>
        )}
      </Card>

      {showCreate && (
        <CreateZoneForm
          onSuccess={() => setShowCreate(false)}
          onCancel={() => setShowCreate(false)}
        />
      )}

      <ConfirmDialog
        open={pendingDeleteId !== null}
        title="Eliminar zona"
        message="¿Estás seguro de eliminar esta zona? Esta acción no se puede deshacer."
        confirmLabel="Eliminar"
        cancelLabel="Cancelar"
        variant="destructive"
        onConfirm={() => {
          if (pendingDeleteId) void handleDeleteConfirm(pendingDeleteId);
        }}
        onCancel={() => setPendingDeleteId(null)}
      />

      {editingZone && (
        <ZoneConfigModal
          zone={editingZone}
          onClose={() => setEditingZone(null)}
        />
      )}
    </div>
  );
}