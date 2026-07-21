import { useState, useCallback } from 'react';
import { AttendanceLevelList } from '../components/AttendanceLevelList';
import { AttendanceLevelForm } from '../components/AttendanceLevelForm';
import { useAttendanceLevels } from '../hooks/useAttendanceLevels';
import { useAttendanceLevelMutations } from '../hooks/useAttendanceLevelMutations';
import type { AttendanceLevelDTO } from '../types';
import { apiClient } from '@/core/api/client';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function AttendanceLevelScreen() {
  const { levels, loading, error, refresh } = useAttendanceLevels();
  const { create, update, remove, saving } = useAttendanceLevelMutations();

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
    try {
      const { data } = await apiClient.get<AttendanceLevelDTO>(
        `/events/${EVENT_ID}/attendance-levels/${level.id}`
      );
      setEditingLevel(data);
      setShowForm(true);
    } catch {
      setFormError('Error al cargar los datos del nivel de asistencia');
    }
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
      global_multiplier: number;
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
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold text-slate-800">Gestión de Niveles de Asistencia</h1>
        {!showForm && (
          <button
            onClick={handleNew}
            className="bg-blue-600 hover:bg-blue-700 text-white py-1.5 px-4 rounded-lg text-sm font-medium transition-colors"
          >
            + Nuevo nivel
          </button>
        )}
      </header>

      <main className="p-6 max-w-3xl mx-auto">
        {formError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {formError}
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
            {error}
          </div>
        )}

        {showForm ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">
              {editingLevel ? 'Editar nivel' : 'Nuevo nivel de asistencia'}
            </h2>
            <AttendanceLevelForm
              initial={editingLevel ? {
                name: editingLevel.name,
                min_people: editingLevel.min_people,
                max_people: editingLevel.max_people,
                global_multiplier: editingLevel.global_multiplier,
              } : null}
              onSave={handleSave}
              onCancel={handleCancel}
              saving={saving}
            />
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Niveles cargados</h2>
            {loading ? (
              <div className="text-center py-8 text-slate-500">Cargando...</div>
            ) : (
              <AttendanceLevelList
                levels={levels}
                onEdit={handleEdit}
                onDelete={handleDelete}
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}
