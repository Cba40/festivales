import { useMemo, useState } from 'react';
import {
  Plus, Pencil, Trash2, Search, X,
  Car, Bus, Utensils, Wrench, LogOut, Hotel, MapPin,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useAppStore } from '../../../core/state/store';
import { useZoneConfigMutations } from '../hooks/useZoneConfigMutations';
import { ZoneCreateModal } from './ZoneCreateModal';
import { ZoneConfigModal } from './ZoneConfigModal';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { ConfirmDialog } from './ui/ConfirmDialog';
import type { Zone } from '../types';

const TYPE_LABELS: Record<string, string> = {
  estacionamiento: 'Estacionamientos',
  transporte: 'Transporte',
  comida: 'Gastronomía',
  servicios: 'Servicios',
  salida: 'Salidas',
  hospedaje: 'Alojamiento',
};

const TYPE_ICONS: Record<string, LucideIcon> = {
  estacionamiento: Car,
  transporte: Bus,
  comida: Utensils,
  servicios: Wrench,
  salida: LogOut,
  hospedaje: Hotel,
};

function normalizeText(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

function formatLocation(zone: Zone): string {
  if (zone.lat === undefined || zone.lng === undefined) return '—';
  return `${zone.lat.toFixed(2)}, ${zone.lng.toFixed(2)}`;
}

interface ZoneGroup {
  type: string;
  zones: Zone[];
}

export function ZoneManagementPanel() {
  const zones = useAppStore((state) => state.zones);
  const { deleteZone, loading, error } = useZoneConfigMutations();
  const [showCreate, setShowCreate] = useState(false);
  const [editingZone, setEditingZone] = useState<Zone | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const groups = useMemo<ZoneGroup[]>(() => {
    const term = normalizeText(searchTerm.trim());
    const filtered = term
      ? zones.filter((zone) => {
          const haystack = normalizeText(
            `${zone.name} ${zone.type} ${zone.subtipo ?? ''}`
          );
          return haystack.includes(term);
        })
      : zones;

    const grouped = new Map<string, Zone[]>();
    for (const zone of filtered) {
      const list = grouped.get(zone.type) ?? [];
      list.push(zone);
      grouped.set(zone.type, list);
    }

    return Array.from(grouped.entries())
      .map(([type, groupZones]) => ({
        type,
        zones: groupZones.sort((a, b) => a.name.localeCompare(b.name, 'es')),
      }))
      .sort((a, b) =>
        (TYPE_LABELS[a.type] ?? a.type).localeCompare(TYPE_LABELS[b.type] ?? b.type, 'es')
      );
  }, [zones, searchTerm]);

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

        <div className="relative mb-4">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar zona por nombre, tipo o subtipo..."
            className="w-full pl-9 pr-9 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
          />
          {searchTerm.length > 0 && (
            <button
              type="button"
              onClick={() => setSearchTerm('')}
              title="Limpiar búsqueda"
              className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 text-slate-400 hover:text-slate-600 rounded-full"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {zones.length === 0 ? (
          <p className="text-sm text-slate-500 italic text-center py-8">
            No hay zonas registradas. Crea la primera usando el botón "+ Nueva Zona".
          </p>
        ) : groups.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-8">
            No se encontraron zonas que coincidan con '{searchTerm.trim()}'.
          </p>
        ) : (
          <div className="space-y-6">
            {groups.map((group) => {
              const Icon = TYPE_ICONS[group.type] ?? MapPin;
              const label = TYPE_LABELS[group.type] ?? group.type;
              return (
                <section key={group.type}>
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-2">
                    <Icon className="w-4 h-4 text-indigo-600" />
                    {label}
                    <span className="text-xs font-normal text-slate-400">
                      {group.zones.length === 1 ? '(1 zona)' : `(${group.zones.length} zonas)`}
                    </span>
                  </h3>
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
                        {group.zones.map((zone) => (
                          <tr key={zone.id} className="border-b border-slate-100 hover:bg-slate-50">
                            <td className="py-3 pr-2 text-slate-800 font-medium">{zone.name}</td>
                            <td className="py-3 pr-2">
                              <Badge variant="neutral">
                                {TYPE_LABELS[zone.type] ?? zone.type}
                              </Badge>
                            </td>
                            <td className="py-3 pr-2 text-slate-600">
                              {zone.capacity.toLocaleString('es-AR')}
                            </td>
                            <td className="py-3 pr-2 text-slate-400 whitespace-nowrap">
                              {formatLocation(zone)}
                            </td>
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
                </section>
              );
            })}
          </div>
        )}
      </Card>

      <ZoneCreateModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onSuccess={() => setShowCreate(false)}
      />

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