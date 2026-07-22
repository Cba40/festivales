import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOperationalEvents } from '../hooks/useOperationalEvents';
import { useOperationalEventMutations } from '../hooks/useOperationalEventMutations';
import { useEventDays } from '../hooks/useEventDays';
import type { OperationalEventDTO, OperationalEventCreatePayload, OperationalEventUpdatePayload } from '../types';

const DEFAULT_EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

const EVENT_TYPE_LABELS: Record<string, string> = {
  accidente: 'Accidente',
  corte_calle: 'Corte de calle',
  tormenta: 'Tormenta',
  evacuacion: 'Evacuación',
  incendio: 'Incendio',
  congestion_extraordinaria: 'Congestión Extraordinaria',
  escenario_finalizado: 'Escenario Finalizado',
  apertura_extraordinaria: 'Apertura Extraordinaria',
  incidente_operativo: 'Incidente Operativo',
  fin_espectaculo: 'Fin de Espectáculo',
  corte_energia: 'Corte de Energía',
};

const EVENT_TYPE_ICONS: Record<string, string> = {
  accidente: '⚠️',
  corte_calle: '🚧',
  tormenta: '⛈️',
  evacuacion: '🚨',
  incendio: '🔥',
  congestion_extraordinaria: '🚗',
  escenario_finalizado: '🎭',
  apertura_extraordinaria: '🚪',
  incidente_operativo: '🔧',
  fin_espectaculo: '🎵',
  corte_energia: '💡',
};

interface EventFormData {
  event_type: string;
  description: string;
  zone_id: string;
  start_min: string;
  end_min: string;
}

const emptyForm: EventFormData = {
  event_type: '',
  description: '',
  zone_id: '',
  start_min: '0',
  end_min: '',
};

function formatMinutos(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
}

function EventCard({
  event,
  onFinalize,
  onEdit,
  onDelete,
  saving,
}: {
  event: OperationalEventDTO;
  onFinalize: (id: string) => void;
  onEdit: (e: OperationalEventDTO) => void;
  onDelete: (id: string) => void;
  saving: boolean;
}) {
  return (
    <div
      className={`rounded-xl border-2 p-4 transition-all ${
        event.is_active
          ? 'border-red-300 bg-red-50 shadow-md'
          : 'border-slate-200 bg-white opacity-70'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <span className="text-2xl flex-shrink-0 mt-0.5">
            {EVENT_TYPE_ICONS[event.event_type] ?? '📌'}
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold text-slate-800">
                {EVENT_TYPE_LABELS[event.event_type] ?? event.event_type}
              </span>
              {event.is_active && (
                <span className="text-xs font-bold uppercase text-red-600 bg-red-100 px-2 py-0.5 rounded-full animate-pulse">
                  Activo
                </span>
              )}
              {!event.is_active && (
                <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                  Finalizado
                </span>
              )}
            </div>
            <p className="text-sm text-slate-600 mt-1 break-words">{event.description}</p>
            <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
              <span>Inicio: {formatMinutos(event.start_min)}</span>
              {event.end_min !== null && <span>Fin: {formatMinutos(event.end_min)}</span>}
              {event.zone_id && <span>Zona: {event.zone_id}</span>}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {event.is_active && (
            <button
              onClick={() => onFinalize(event.id)}
              disabled={saving}
              className="text-xs font-medium px-2.5 py-1.5 rounded bg-green-600 hover:bg-green-700 text-white disabled:opacity-50"
            >
              Finalizar
            </button>
          )}
          <button
            onClick={() => onEdit(event)}
            className="text-xs font-medium px-2.5 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-600"
          >
            Editar
          </button>
          <button
            onClick={() => onDelete(event.id)}
            disabled={saving}
            className="text-xs font-medium px-2.5 py-1.5 rounded bg-red-100 hover:bg-red-200 text-red-600 disabled:opacity-50"
          >
            Eliminar
          </button>
        </div>
      </div>
    </div>
  );
}

function EventFormModal({
  initial,
  eventDayId,
  onSave,
  onClose,
  saving,
}: {
  initial: EventFormData;
  eventDayId: string;
  onSave: (payload: OperationalEventCreatePayload | OperationalEventUpdatePayload) => void;
  onClose: () => void;
  saving: boolean;
}) {
  const [form, setForm] = useState<EventFormData>(initial);
  const isEditing = !!initial.event_type && initial.event_type !== '';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.event_type || !form.description.trim()) return;
    const payload: OperationalEventCreatePayload | OperationalEventUpdatePayload = isEditing
      ? {
          event_type: form.event_type as OperationalEventCreatePayload['event_type'],
          description: form.description,
          zone_id: form.zone_id || null,
          start_min: parseInt(form.start_min) || 0,
          end_min: form.end_min ? parseInt(form.end_min) : null,
        }
      : {
          event_day_id: eventDayId,
          event_type: form.event_type as OperationalEventCreatePayload['event_type'],
          description: form.description,
          zone_id: form.zone_id || null,
          start_min: parseInt(form.start_min) || 0,
          end_min: form.end_min ? parseInt(form.end_min) : null,
        };
    onSave(payload);
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-slate-800 mb-4">
          {isEditing ? 'Editar Evento' : 'Nuevo Evento Operativo'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tipo de evento</label>
            <select
              value={form.event_type}
              onChange={(e) => setForm((f) => ({ ...f, event_type: e.target.value }))}
              required
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Seleccionar...</option>
              {Object.entries(EVENT_TYPE_LABELS).map(([key, label]) => (
                <option key={key} value={key}>{EVENT_TYPE_ICONS[key]} {label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Descripción</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              required
              rows={3}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Describí el evento..."
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Inicio (min)</label>
              <input
                type="number"
                value={form.start_min}
                onChange={(e) => setForm((f) => ({ ...f, start_min: e.target.value }))}
                required
                min={0}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Fin (min, opcional)</label>
              <input
                type="number"
                value={form.end_min}
                onChange={(e) => setForm((f) => ({ ...f, end_min: e.target.value }))}
                min={0}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Zona (ID, opcional)</label>
            <input
              type="text"
              value={form.zone_id}
              onChange={(e) => setForm((f) => ({ ...f, zone_id: e.target.value }))}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="ID de la zona afectada"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={saving || !form.event_type || !form.description.trim()}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-lg text-sm disabled:opacity-50"
            >
              {saving ? 'Guardando...' : isEditing ? 'Guardar Cambios' : 'Registrar Evento'}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm text-slate-600 hover:bg-slate-50"
            >
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function OperationalEventScreen() {
  const navigate = useNavigate();
  const { eventDays, loading: loadingDays } = useEventDays(DEFAULT_EVENT_ID);
  const [selectedDayId, setSelectedDayId] = useState<string | null>(null);
  const { events, loading, error, refresh } = useOperationalEvents(selectedDayId);
  const { create, update, remove, finalize, saving, error: mutationError } = useOperationalEventMutations();
  const [showForm, setShowForm] = useState(false);
  const [editingEvent, setEditingEvent] = useState<OperationalEventDTO | null>(null);
  const [showFinalized, setShowFinalized] = useState(false);

  useEffect(() => {
    if (eventDays.length > 0 && !selectedDayId) {
      setSelectedDayId(eventDays[0].id);
    }
  }, [eventDays, selectedDayId]);

  const activeEvents = events.filter((e) => e.is_active);
  const finalizedEvents = events.filter((e) => !e.is_active);

  const handleSave = useCallback(
    async (payload: OperationalEventCreatePayload | OperationalEventUpdatePayload) => {
      let result;
      if (editingEvent) {
        const { event_day_id, ...rest } = payload as OperationalEventCreatePayload;
        result = await update(editingEvent.id, rest);
      } else {
        result = await create(payload as OperationalEventCreatePayload);
      }
      if (result) {
        setShowForm(false);
        setEditingEvent(null);
        refresh();
      }
    },
    [editingEvent, create, update, refresh]
  );

  const handleEdit = useCallback((event: OperationalEventDTO) => {
    setEditingEvent(event);
    setShowForm(true);
  }, []);

  const handleFinalize = useCallback(
    async (id: string) => {
      const result = await finalize(id);
      if (result) refresh();
    },
    [finalize, refresh]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      const ok = await remove(id);
      if (ok) refresh();
    },
    [remove, refresh]
  );

  const openCreateForm = useCallback(() => {
    setEditingEvent(null);
    setShowForm(true);
  }, []);

  const closeForm = useCallback(() => {
    setShowForm(false);
    setEditingEvent(null);
  }, []);

  const formInitial: EventFormData = editingEvent
    ? {
        event_type: editingEvent.event_type,
        description: editingEvent.description,
        zone_id: editingEvent.zone_id ?? '',
        start_min: editingEvent.start_min.toString(),
        end_min: editingEvent.end_min !== null ? editingEvent.end_min.toString() : '',
      }
    : emptyForm;

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold text-slate-800">Eventos Operativos</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={refresh}
            disabled={loading}
            className="text-sm px-3 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-600 font-medium"
          >
            {loading ? 'Cargando...' : 'Actualizar'}
          </button>
          <button
            onClick={openCreateForm}
            className="bg-red-600 hover:bg-red-700 text-white px-4 py-1.5 rounded-lg text-sm font-bold shadow-sm"
          >
            + Nuevo Evento
          </button>
        </div>
      </header>

      <main className="p-6 max-w-4xl mx-auto">
        {error && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
            {error}
          </div>
        )}

        {mutationError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {mutationError}
          </div>
        )}

        {/* EventDay selector */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-1">Jornada</label>
          <select
            value={selectedDayId ?? ''}
            onChange={(e) => setSelectedDayId(e.target.value || null)}
            disabled={loadingDays}
            className="w-full max-w-xs px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <option value="">Seleccionar jornada...</option>
            {eventDays.map((d) => (
              <option key={d.id} value={d.id}>
                {d.date} — {d.day_of_week}
              </option>
            ))}
          </select>
        </div>

        {!selectedDayId ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-10 text-center text-slate-500">
            Seleccioná una jornada para ver sus eventos operativos.
          </div>
        ) : loading ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-10 text-center text-slate-500">
            Cargando eventos...
          </div>
        ) : (
          <>
            {/* Active events */}
            <section className="mb-8">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                  <span className="w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse" />
                  Eventos Activos
                  <span className="text-sm font-normal text-slate-500">({activeEvents.length})</span>
                </h2>
              </div>
              {activeEvents.length === 0 ? (
                <div className="bg-white rounded-xl border-2 border-dashed border-slate-200 p-8 text-center text-slate-400">
                  No hay eventos activos en esta jornada.
                </div>
              ) : (
                <div className="space-y-3">
                  {activeEvents.map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      onFinalize={handleFinalize}
                      onEdit={handleEdit}
                      onDelete={handleDelete}
                      saving={saving}
                    />
                  ))}
                </div>
              )}
            </section>

            {/* Finalized events */}
            <section>
              <button
                onClick={() => setShowFinalized((v) => !v)}
                className="flex items-center justify-between w-full text-left"
              >
                <h2 className="text-lg font-bold text-slate-600">
                  Eventos Finalizados ({finalizedEvents.length})
                </h2>
                <span className="text-slate-400 text-lg">{showFinalized ? '▼' : '▶'}</span>
              </button>
              {showFinalized && (
                <div className="mt-3 space-y-2">
                  {finalizedEvents.length === 0 ? (
                    <div className="bg-white rounded-xl border border-slate-200 p-6 text-center text-slate-400 text-sm">
                      No hay eventos finalizados.
                    </div>
                  ) : (
                    finalizedEvents.map((event) => (
                      <EventCard
                        key={event.id}
                        event={event}
                        onFinalize={handleFinalize}
                        onEdit={handleEdit}
                        onDelete={handleDelete}
                        saving={saving}
                      />
                    ))
                  )}
                </div>
              )}
            </section>
          </>
        )}
      </main>

      {showForm && selectedDayId && (
        <EventFormModal
          initial={formInitial}
          eventDayId={selectedDayId}
          onSave={handleSave}
          onClose={closeForm}
          saving={saving}
        />
      )}
    </div>
  );
}
