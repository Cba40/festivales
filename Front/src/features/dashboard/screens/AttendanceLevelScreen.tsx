import { useState, useCallback, useEffect } from 'react';
import { AttendanceLevelList } from '../components/AttendanceLevelList';
import { AttendanceLevelForm } from '../components/AttendanceLevelForm';
import { useAttendanceLevels } from '../hooks/useAttendanceLevels';
import { useAttendanceLevelMutations } from '../hooks/useAttendanceLevelMutations';
import { useEventDays } from '../hooks/useEventDays';
import type { AttendanceLevelDTO } from '../types';
import { apiClient } from '@/core/api/client';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function AttendanceLevelScreen() {
  const { eventDays, loading: loadingDays, error: daysError } = useEventDays(EVENT_ID);
  const [selectedDayId, setSelectedDayId] = useState<string | null>(null);

  useEffect(() => {
    if (eventDays.length === 0) {
      setSelectedDayId(null);
      return;
    }

    if (!selectedDayId) {
      const nextSelectedDay = eventDays.find((day) => day.is_active) ?? eventDays[0];
      setSelectedDayId(nextSelectedDay.id);
      return;
    }

    const exists = eventDays.some((day) => day.id === selectedDayId);
    if (!exists) {
      setSelectedDayId(eventDays[0].id);
    }
  }, [eventDays, selectedDayId]);

  const { levels, loading, error, refresh } = useAttendanceLevels(EVENT_ID, selectedDayId ?? '');
  const { create, update, remove, saving } = useAttendanceLevelMutations(EVENT_ID, selectedDayId ?? '');

  const [showForm, setShowForm] = useState(false);
  const [editingLevel, setEditingLevel] = useState<AttendanceLevelDTO | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const handleNew = () => {
    if (!selectedDayId) return;
    setEditingLevel(null);
    setFormError(null);
    setShowForm(true);
  };

  const handleEdit = useCallback(async (level: AttendanceLevelDTO) => {
    if (!selectedDayId) return;
    setFormError(null);
    try {
      const { data } = await apiClient.get<AttendanceLevelDTO>(
        `/events/${EVENT_ID}/days/${selectedDayId}/attendance-levels/${level.id}`
      );
      setEditingLevel(data);
      setShowForm(true);
    } catch {
      setFormError('Error al cargar los datos del nivel de asistencia');
    }
  }, [selectedDayId]);

  const handleDelete = useCallback(
    async (id: string) => {
      if (!selectedDayId) return;
      if (!window.confirm('¿Eliminar este nivel de asistencia? Esta acción no se puede deshacer.')) return;
      const ok = await remove(id);
      if (ok) refresh();
    },
    [remove, refresh, selectedDayId]
  );

  const handleSave = useCallback(
    async (payload: {
      name: string;
      min_people: number;
      max_people?: number | null;
    }) => {
      if (!selectedDayId) return;
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
    [editingLevel, create, update, refresh, selectedDayId]
  );

  const handleCancel = () => {
    setShowForm(false);
    setEditingLevel(null);
    setFormError(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center gap-4">
        <h1 className="text-xl font-bold text-slate-800">Gestión de Niveles de Asistencia</h1>

        <div className="flex items-center gap-3">
          <select
            value={selectedDayId ?? ''}
            onChange={(e) => setSelectedDayId(e.target.value || null)}
            disabled={loadingDays || eventDays.length === 0}
            className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <option value="">Seleccionar jornada...</option>
            {eventDays.map((day) => (
              <option key={day.id} value={day.id}>
                {day.date} {day.is_active ? '(Hoy)' : ''}
              </option>
            ))}
          </select>

          {!showForm && selectedDayId && (
            <button
              onClick={handleNew}
              className="bg-blue-600 hover:bg-blue-700 text-white py-1.5 px-4 rounded-lg text-sm font-medium transition-colors"
            >
              + Nuevo nivel
            </button>
          )}
        </div>
      </header>

      <main className="p-6 max-w-3xl mx-auto">
        {daysError && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
            {daysError}
          </div>
        )}

        {formError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {formError}
          </div>
        )}

        {!selectedDayId && !loadingDays && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-10 text-center text-slate-500">
            Seleccioná una jornada para ver sus niveles de asistencia.
          </div>
        )}

        {selectedDayId && error && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
            {error}
          </div>
        )}

        {showForm && selectedDayId ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">
              {editingLevel ? 'Editar nivel' : 'Nuevo nivel de asistencia'}
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
          </div>
        ) : selectedDayId ? (
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
        ) : null}
      </main>
    </div>
  );
}
