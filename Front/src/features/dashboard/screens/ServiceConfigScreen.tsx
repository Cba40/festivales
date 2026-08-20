import { useState, useCallback } from 'react';
import { ServiceConfigList } from '../components/ServiceConfigList';
import { ServiceConfigForm } from '../components/ServiceConfigForm';
import { useServiceConfigs } from '../hooks/useServiceConfigs';
import { useServiceConfigMutations } from '../hooks/useServiceConfigMutations';
import { useEventDays } from '../hooks/useEventDays';
import { useZoneTypes } from '../hooks/useZoneBehaviors';
import type { ServiceConfigDTO } from '../types';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function ServiceConfigScreen() {
  const { data: configs, loading, error, refresh } = useServiceConfigs();
  const { eventDays } = useEventDays(EVENT_ID);
  const { zoneTypes } = useZoneTypes();
  const { create, update, remove, saving, error: mutationError } =
    useServiceConfigMutations(refresh);

  const availableZoneTypes = zoneTypes.filter(
    (zt) => zt.slug !== 'estacionamiento'
  );

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<ServiceConfigDTO | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const handleNew = () => {
    setEditing(null);
    setFormError(null);
    setShowForm(true);
  };

  const handleEdit = useCallback((config: ServiceConfigDTO) => {
    setFormError(null);
    setEditing(config);
    setShowForm(true);
  }, []);

  const handleDelete = useCallback(
    async (id: string) => {
      if (!window.confirm('¿Eliminar esta configuración de servicios? Esta acción no se puede deshacer.')) return;
      await remove(id);
    },
    [remove]
  );

  const handleSave = useCallback(
    async (payload: {
      zone_type_id: string;
      subtipo?: string | null;
      event_day_id?: string | null;
      average_duration_min: number;
    }) => {
      setFormError(null);
      const result = editing
        ? await update(editing.id, payload)
        : await create(payload);
      if (result) {
        setShowForm(false);
        setEditing(null);
      } else {
        setFormError(mutationError ?? 'Error al guardar. Revisá los datos e intentá de nuevo.');
      }
    },
    [editing, create, update, mutationError]
  );

  const handleCancel = () => {
    setShowForm(false);
    setEditing(null);
    setFormError(null);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Configuración de Servicios</h1>
        {!showForm && (
          <button
            onClick={handleNew}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Nueva configuración
          </button>
        )}
      </div>

      {error && <div className="text-red-600 mb-4">{error}</div>}

      {loading ? (
        <div className="text-center py-8">Cargando configuraciones...</div>
      ) : (
        <>
          {showForm && (
            <>
              {formError && <div className="text-red-600 mb-4">{formError}</div>}
              <ServiceConfigForm
                initial={editing}
                zoneTypes={availableZoneTypes}
                eventDays={eventDays}
                onSave={handleSave}
                onCancel={handleCancel}
                saving={saving}
              />
            </>
          )}

          {!showForm && (
            <ServiceConfigList
              configs={configs}
              zoneTypes={zoneTypes}
              eventDays={eventDays}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          )}
        </>
      )}
    </div>
  );
}