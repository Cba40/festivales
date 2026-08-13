import { useState, useCallback } from 'react';
import { AttendanceLevelList } from '../components/AttendanceLevelList';
import { AttendanceLevelForm } from '../components/AttendanceLevelForm';
import { useAttendanceLevels } from '../hooks/useAttendanceLevels';
import { useAttendanceLevelMutations } from '../hooks/useAttendanceLevelMutations';
import type { AttendanceLevelDTO } from '../types';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function AttendanceLevelScreen() {
  const { levels, loading, error, refresh } = useAttendanceLevels(EVENT_ID);
  const { create, update, remove, saving } = useAttendanceLevelMutations(EVENT_ID);

  const [showForm, setShowForm] = useState(false);
  const [editingLevel, setEditingLevel] = useState<AttendanceLevelDTO | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const handleNew = () => {
    setEditingLevel(null);
    setFormError(null);
    setShowForm(true);
  };

  const handleEdit = useCallback(async (level: AttendanceLevelDTO) => {
    setFormError(null);
    setEditingLevel(level);
    setShowForm(true);
  }, []);

  const handleDelete = useCallback(
    async (id: string) => {
      if (!window.confirm('¿Eliminar este nivel de asistencia? Esta acción no se puede deshacer.')) return;
      const ok = await remove(id);
      if (ok) refresh();
    },
    [remove, refresh]
  );

  const handleSave = useCallback(
    async (payload: {
      name: string;
      min_people: number;
      max_people?: number | null;
    }) => {
      setFormError(null);
      let result: AttendanceLevelDTO | null;
      if (editingLevel) {
        result = await update(editingLevel.id, payload);
      } else {
        result = await create(payload);
      }
      if (result) {
        setShowForm(false);
        setEditingLevel(null);
        refresh();
      } else {
        setFormError('Error al guardar. Revisá los datos e intentá de nuevo.');
      }
    },
    [editingLevel, create, update, refresh]
  );

  const handleCancel = () => {
    setShowForm(false);
    setEditingLevel(null);
    setFormError(null);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Niveles de Asistencia</h1>
        {!showForm && (
          <button
            onClick={handleNew}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Nuevo Nivel
          </button>
        )}
      </div>

      {error && <div className="text-red-600 mb-4">{error}</div>}

      {loading ? (
        <div className="text-center py-8">Cargando niveles...</div>
      ) : (
        <>
          {showForm && (
            <>
              {formError && <div className="text-red-600 mb-4">{formError}</div>}
              <AttendanceLevelForm
                initial={editingLevel ? {
                  name: editingLevel.name,
                  min_people: editingLevel.min_people,
                  max_people: editingLevel.max_people,
                } : null}
                onSave={handleSave}
                onCancel={handleCancel}
                saving={saving}
              />
            </>
          )}

          {!showForm && (
            <AttendanceLevelList
              levels={levels}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          )}
        </>
      )}
    </div>
  );
}
