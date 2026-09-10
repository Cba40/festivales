import { useState, useCallback } from 'react';
import { Plus } from 'lucide-react';
import { EventDayList } from '../components/EventDayList';
import { EventDayForm } from '../components/EventDayForm';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
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
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

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

  const handleDeleteConfirm = useCallback(
    async (id: string) => {
      const ok = await remove(id);
      setPendingDeleteId(null);
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
    <main className="p-4 sm:p-6 max-w-5xl mx-auto space-y-6">
      <Card variant="standard">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
          <h1 className="text-xl font-bold text-slate-800">Gestión de Días del Evento</h1>
          {!showForm && (
            <Button onClick={handleNew}>
              <Plus className="w-4 h-4" />
              Nuevo día
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
        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
          {error}
        </div>
      )}

      {showForm ? (
        <Card variant="standard">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">
            {editingDay ? 'Editar día' : 'Nuevo día del evento'}
          </h2>
          <EventDayForm
            eventDay={editingDay}
            eventId={EVENT_ID}
            onSave={handleSave}
            onCancel={handleCancel}
            saving={saving}
          />
        </Card>
      ) : (
        <Card variant="standard">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Días cargados</h2>
          {loading ? (
            <div className="text-center py-8 text-slate-500">Cargando...</div>
          ) : (
            <>
              <EventDayList
                eventDays={eventDays}
                onEdit={handleEdit}
                onRequestDelete={setPendingDeleteId}
              />
              <ConfirmDialog
                open={pendingDeleteId !== null}
                title="Eliminar día del evento"
                message="¿Eliminar este día del evento? Esta acción no se puede deshacer."
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