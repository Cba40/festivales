import { useState, useCallback } from 'react';
import { Plus } from 'lucide-react';
import { AttendanceLevelList } from '../components/AttendanceLevelList';
import { AttendanceLevelForm } from '../components/AttendanceLevelForm';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
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
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

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

  const handleDeleteConfirm = useCallback(
    async (id: string) => {
      const ok = await remove(id);
      setPendingDeleteId(null);
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
    <main className="p-4 sm:p-6 max-w-5xl mx-auto space-y-6">
      <Card variant="standard">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
          <h1 className="text-xl font-bold text-slate-800">Niveles de Asistencia</h1>
          {!showForm && (
            <Button onClick={handleNew}>
              <Plus className="w-4 h-4" />
              Nuevo Nivel
            </Button>
          )}
        </div>
      </Card>

      {formError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {formError}
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <Card variant="standard">
          <div className="text-center py-8 text-slate-500">Cargando niveles...</div>
        </Card>
      ) : (
        <Card variant="standard">
          {showForm ? (
            <>
              <h2 className="text-lg font-semibold text-slate-800 mb-4">
                {editingLevel ? 'Editar nivel de asistencia' : 'Nuevo nivel de asistencia'}
              </h2>
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
          ) : (
            <>
              <AttendanceLevelList
                levels={levels}
                onEdit={handleEdit}
                onRequestDelete={setPendingDeleteId}
              />
              <ConfirmDialog
                open={pendingDeleteId !== null}
                title="Eliminar nivel de asistencia"
                message="¿Eliminar este nivel de asistencia? Esta acción no se puede deshacer."
                confirmLabel="Eliminar"
                cancelLabel="Cancelar"
                variant="destructive"
                onConfirm={() => {
                  if (pendingDeleteId) void handleDeleteConfirm(pendingDeleteId);
                }}
                onCancel={() => setPendingDeleteId(null)}
              />
            </>
          )}
        </Card>
      )}
    </main>
  );
}