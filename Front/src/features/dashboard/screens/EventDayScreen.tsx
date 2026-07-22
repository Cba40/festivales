import { useState, useCallback } from 'react';
import { EventDayList } from '../components/EventDayList';
import { EventDayForm } from '../components/EventDayForm';
import { useEventDays } from '../hooks/useEventDays';
import { useEventDayMutations } from '../hooks/useEventDayMutations';
import type { EventDaySummary, EventDay, EventDayCreatePayload } from '../types';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export function EventDayScreen() {
  const { eventDays, loading, error, refresh } = useEventDays(EVENT_ID);
  const { create, update, remove, saving } = useEventDayMutations(EVENT_ID);

  const [showForm, setShowForm] = useState(false);
  const [editingDay, setEditingDay] = useState<EventDay | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const handleNew = () => {
    setEditingDay(null);
    setFormError(null);
    setShowForm(true);
  };

  const handleEdit = useCallback(async (day: EventDaySummary) => {
    setFormError(null);
    try {
      const { data } = await apiClient.get<EventDay>(
        endpoints.eventDays.byId(EVENT_ID, day.id)
      );
      setEditingDay(data);
      setShowForm(true);
    } catch {
      setFormError('Error al cargar los datos del día');
    }
  }, []);

  const handleDelete = useCallback(
    async (id: string) => {
      if (!window.confirm('¿Eliminar este día del evento? Esta acción no se puede deshacer.')) return;
      const ok = await remove(id);
      if (ok) refresh();
    },
    [remove, refresh]
  );

  const handleSave = useCallback(
    async (payload: EventDayCreatePayload) => {
      setFormError(null);
      const result = editingDay
        ? await update(editingDay.id, payload)
        : await create(payload);
      if (result) {
        setShowForm(false);
        setEditingDay(null);
        refresh();
      } else {
        setFormError('Error al guardar. Revisá los datos e intentá de nuevo.');
      }
    },
    [editingDay, create, update, refresh]
  );

  const handleCancel = () => {
    setShowForm(false);
    setEditingDay(null);
    setFormError(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold text-slate-800">Gestión de Días del Evento</h1>
        {!showForm && (
          <button
            onClick={handleNew}
            className="bg-blue-600 hover:bg-blue-700 text-white py-1.5 px-4 rounded-lg text-sm font-medium transition-colors"
          >
            + Nuevo día
          </button>
        )}
      </header>

      <main className="p-6 max-w-5xl mx-auto">
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
              {editingDay ? 'Editar día' : 'Nuevo día del evento'}
            </h2>
            <EventDayForm
              eventDay={editingDay}
              onSave={handleSave}
              onCancel={handleCancel}
              saving={saving}
            />
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Días cargados</h2>
            {loading ? (
              <div className="text-center py-8 text-slate-500">Cargando...</div>
            ) : (
              <EventDayList
                eventDays={eventDays}
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
