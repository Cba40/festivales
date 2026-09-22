import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import { Ban, Megaphone, Plus, Pencil, Power, Search, Trash2, X } from 'lucide-react';
import { DashboardHeader } from '../components/DashboardHeader';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { RefreshButton } from '../components/ui/RefreshButton';
import { SectionTabs } from '../components/ui/SectionTabs';
import {
  useTransportAlerts,
} from '../hooks/useTransportAlerts';
import { useOperatorMessages } from '../hooks/useOperatorMessages';
import type {
  AlertType,
  OperatorMessageDTO,
  OperatorMessageCreatePayload,
  OperatorMessageUpdatePayload,
  TransportAlertDTO,
  TransportAlertCreatePayload,
  TransportAlertUpdatePayload,
} from '../types';

const DEFAULT_EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

interface LineOption {
  id: string;
  name: string;
  type: string;
}

const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  info: 'Información',
  warning: 'Aviso',
  disruption: 'Interrupción',
  closure: 'Clausura',
};

const ALERT_TYPE_BADGES: Record<AlertType, 'info' | 'warning' | 'error' | 'neutral'> = {
  info: 'info',
  warning: 'warning',
  disruption: 'error',
  closure: 'neutral',
};

const PRIORITY_LABELS = {
  normal: 'Informativo',
  high: 'Alta prioridad',
  urgent: 'Urgente',
} as const;

const PRIORITY_BADGES = {
  normal: 'neutral',
  high: 'warning',
  urgent: 'error',
} as const;

const STATUS_LABELS = {
  draft: 'Borrador',
  published: 'Publicado',
  cancelled: 'Cancelado',
} as const;

const STATUS_BADGES = {
  draft: 'neutral',
  published: 'success',
  cancelled: 'error',
} as const;

function normalizeText(value: string): string {
  return value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function toLocalDateTimeInput(d: Date): string {
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function isoToLocalDateTimeInput(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  return toLocalDateTimeInput(d);
}

function localDateTimeToIso(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  return isNaN(d.getTime()) ? null : d.toISOString();
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString('es-AR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function isExpired(validUntil: string): boolean {
  return Date.now() >= new Date(validUntil).getTime();
}

function getAlertStatus(alert: TransportAlertDTO): { label: string; variant: 'success' | 'warning' | 'neutral' } {
  if (!alert.is_active) return { label: 'Desactivada', variant: 'neutral' };
  if (isExpired(alert.valid_until)) return { label: 'Vencida', variant: 'warning' };
  return { label: 'Activa', variant: 'success' };
}

interface AlertFormData {
  alert_type: string;
  title: string;
  description: string;
  line_id: string;
  valid_from: string;
  valid_until: string;
  is_active: boolean;
}

const emptyAlertForm: AlertFormData = {
  alert_type: '',
  title: '',
  description: '',
  line_id: '',
  valid_from: '',
  valid_until: '',
  is_active: true,
};

function AlertFormModal({
  initial,
  lines,
  isEditing,
  onSave,
  onClose,
  saving,
}: {
  initial: AlertFormData;
  lines: LineOption[];
  isEditing: boolean;
  onSave: (payload: TransportAlertCreatePayload | TransportAlertUpdatePayload) => void;
  onClose: () => void;
  saving: boolean;
}) {
  const [form, setForm] = useState<AlertFormData>(initial);

  const temporalOk =
    !!form.valid_from && !!form.valid_until
      ? new Date(form.valid_until).getTime() > new Date(form.valid_from).getTime()
      : false;

  const canSubmit =
    !saving &&
    !!form.alert_type &&
    form.title.trim().length > 0 &&
    form.description.trim().length > 0 &&
    !!form.valid_from &&
    !!form.valid_until &&
    temporalOk;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    const validFromIso = localDateTimeToIso(form.valid_from)!;
    const validUntilIso = localDateTimeToIso(form.valid_until)!;
    const lineId = form.line_id.trim() === '' ? null : form.line_id.trim();
    if (isEditing) {
      const payload: TransportAlertUpdatePayload = {
        alert_type: form.alert_type as AlertType,
        title: form.title.trim(),
        description: form.description.trim(),
        line_id: lineId,
        valid_from: validFromIso,
        valid_until: validUntilIso,
        is_active: form.is_active,
      };
      onSave(payload);
    } else {
      const payload: TransportAlertCreatePayload = {
        event_id: DEFAULT_EVENT_ID,
        alert_type: form.alert_type as AlertType,
        title: form.title.trim(),
        description: form.description.trim(),
        line_id: lineId,
        valid_from: validFromIso,
        valid_until: validUntilIso,
      };
      onSave(payload);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto shadow-xl">
        <h2 className="text-lg font-bold text-slate-800 mb-4">
          {isEditing ? 'Editar Alerta' : 'Nueva Alerta'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tipo de alerta *</label>
            <select
              value={form.alert_type}
              onChange={(e) => setForm((f) => ({ ...f, alert_type: e.target.value }))}
              required
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">Seleccionar...</option>
              {(Object.keys(ALERT_TYPE_LABELS) as AlertType[]).map((key) => (
                <option key={key} value={key}>{ALERT_TYPE_LABELS[key]}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Título *</label>
            <input
              type="text"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              required
              maxLength={200}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="Ej: Corte en Av. Córdoba por espectáculo"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Descripción *</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              rows={3}
              required
              maxLength={2000}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="Detalle de la alerta..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Línea de transporte (opcional)</label>
            <select
              value={form.line_id}
              onChange={(e) => setForm((f) => ({ ...f, line_id: e.target.value }))}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">General (sin línea específica)</option>
              {lines.map((l) => (
                <option key={l.id} value={l.id}>{l.name} — {l.type}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Fecha y hora desde *</label>
              <input
                type="datetime-local"
                value={form.valid_from}
                onChange={(e) => setForm((f) => ({ ...f, valid_from: e.target.value }))}
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Fecha y hora hasta *</label>
              <input
                type="datetime-local"
                value={form.valid_until}
                onChange={(e) => setForm((f) => ({ ...f, valid_until: e.target.value }))}
                required
                className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 ${
                  form.valid_from && form.valid_until && !temporalOk
                    ? 'border-red-400 bg-red-50'
                    : 'border-slate-300'
                }`}
              />
              {form.valid_from && form.valid_until && !temporalOk && (
                <p className="text-xs text-red-500 mt-1">La fecha hasta debe ser posterior a la de inicio</p>
              )}
            </div>
          </div>

          {isEditing && (
            <div className="flex items-center gap-3 py-1">
              <input
                type="checkbox"
                id="alert_is_active"
                checked={form.is_active}
                onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              <label htmlFor="alert_is_active" className="text-sm font-medium text-slate-700 select-none cursor-pointer">
                Alerta activa
              </label>
            </div>
          )}

          <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-4">
            <Button type="submit" variant="primary" disabled={!canSubmit || saving}>
              {saving ? 'Guardando...' : isEditing ? 'Guardar Cambios' : 'Crear Alerta'}
            </Button>
            <Button type="button" variant="secondary" onClick={onClose} disabled={saving}>
              Cancelar
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

interface MessageFormData {
  title: string;
  description: string;
  priority: string;
  line_id: string;
  publish_at: string;
  expires_at: string;
}

const emptyMessageForm: MessageFormData = {
  title: '',
  description: '',
  priority: 'normal',
  line_id: '',
  publish_at: '',
  expires_at: '',
};

function MessageFormModal({
  initial,
  lines,
  isEditing,
  onSave,
  onClose,
  saving,
}: {
  initial: MessageFormData;
  lines: LineOption[];
  isEditing: boolean;
  onSave: (payload: OperatorMessageCreatePayload | OperatorMessageUpdatePayload) => void;
  onClose: () => void;
  saving: boolean;
}) {
  const [form, setForm] = useState<MessageFormData>(initial);

  const temporalOk =
    form.expires_at.trim() === '' ||
    new Date(form.expires_at).getTime() > new Date(form.publish_at).getTime();

  const canSubmit =
    !saving &&
    form.title.trim().length > 0 &&
    form.description.trim().length > 0 &&
    !!form.publish_at &&
    (form.expires_at.trim() === '' || temporalOk);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    const publishAtIso = localDateTimeToIso(form.publish_at)!;
    const expiresAtIso =
      form.expires_at.trim() === '' ? null : localDateTimeToIso(form.expires_at);
    const lineId = form.line_id.trim() === '' ? null : form.line_id.trim();
    if (isEditing) {
      const payload: OperatorMessageUpdatePayload = {
        title: form.title.trim(),
        description: form.description.trim(),
        priority: form.priority as OperatorMessageUpdatePayload['priority'],
        line_id: lineId,
        publish_at: publishAtIso,
        expires_at: expiresAtIso,
      };
      onSave(payload);
    } else {
      const payload: OperatorMessageCreatePayload = {
        event_id: DEFAULT_EVENT_ID,
        title: form.title.trim(),
        description: form.description.trim(),
        priority: form.priority as OperatorMessageCreatePayload['priority'],
        line_id: lineId,
        publish_at: publishAtIso,
        expires_at: expiresAtIso,
      };
      onSave(payload);
    }
  };

  const priorityKeys = Object.keys(PRIORITY_LABELS) as Array<keyof typeof PRIORITY_LABELS>;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto shadow-xl">
        <h2 className="text-lg font-bold text-slate-800 mb-4">
          {isEditing ? 'Editar Mensaje' : 'Nuevo Mensaje'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Título *</label>
            <input
              type="text"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              required
              maxLength={200}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="Ej: Refuerzo de colectivos al cierre del evento"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Descripción *</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              rows={3}
              required
              maxLength={2000}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="Contenido del mensaje..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Prioridad *</label>
            <select
              value={form.priority}
              onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))}
              required
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              {priorityKeys.map((key) => (
                <option key={key} value={key}>{PRIORITY_LABELS[key]}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Línea de transporte (opcional)</label>
            <select
              value={form.line_id}
              onChange={(e) => setForm((f) => ({ ...f, line_id: e.target.value }))}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">General (sin línea específica)</option>
              {lines.map((l) => (
                <option key={l.id} value={l.id}>{l.name} — {l.type}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Publicar desde *</label>
              <input
                type="datetime-local"
                value={form.publish_at}
                onChange={(e) => setForm((f) => ({ ...f, publish_at: e.target.value }))}
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Expira (opcional)</label>
              <input
                type="datetime-local"
                value={form.expires_at}
                onChange={(e) => setForm((f) => ({ ...f, expires_at: e.target.value }))}
                className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 ${
                  form.expires_at.trim() !== '' && !temporalOk
                    ? 'border-red-400 bg-red-50'
                    : 'border-slate-300'
                }`}
              />
              {form.expires_at.trim() !== '' && !temporalOk && (
                <p className="text-xs text-red-500 mt-1">La expiración debe ser posterior a la publicación</p>
              )}
            </div>
          </div>

          <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-4">
            <Button type="submit" variant="primary" disabled={!canSubmit || saving}>
              {saving ? 'Guardando...' : isEditing ? 'Guardar Cambios' : 'Crear Mensaje'}
            </Button>
            <Button type="button" variant="secondary" onClick={onClose} disabled={saving}>
              Cancelar
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

export function AlertManagementScreen() {
  const {
    alerts,
    loading: loadingAlerts,
    error: alertsError,
    refresh: refreshAlerts,
    create: createAlert,
    update: updateAlert,
    remove: removeAlert,
    deactivate: deactivateAlert,
    saving,
    actionError,
  } = useTransportAlerts(DEFAULT_EVENT_ID);
  const {
    messages,
    loading: loadingMessages,
    error: messagesError,
    refresh: refreshMessages,
    create: createMessage,
    update: updateMessage,
    publish: publishMessage,
    cancel: cancelMessage,
    remove: removeMessage,
    saving: savingMessages,
    actionError: messagesActionError,
  } = useOperatorMessages(DEFAULT_EVENT_ID);

  const [activeSection, setActiveSection] = useState<'alerts' | 'messages'>('alerts');
  const [searchTerm, setSearchTerm] = useState('');
  const [showAlertForm, setShowAlertForm] = useState(false);
  const [editingAlert, setEditingAlert] = useState<TransportAlertDTO | null>(null);
  const [showMessageForm, setShowMessageForm] = useState(false);
  const [editingMessage, setEditingMessage] = useState<OperatorMessageDTO | null>(null);
  const [pendingDeactivateAlertId, setPendingDeactivateAlertId] = useState<string | null>(null);
  const [pendingDeleteAlertId, setPendingDeleteAlertId] = useState<string | null>(null);
  const [pendingCancelMessageId, setPendingCancelMessageId] = useState<string | null>(null);
  const [pendingDeleteMessageId, setPendingDeleteMessageId] = useState<string | null>(null);
  const [lines, setLines] = useState<LineOption[]>([]);

  const loadLines = useCallback(async () => {
    try {
      const res = await apiClient.get<LineOption[]>(
        endpoints.transportAdmin.lines.list(DEFAULT_EVENT_ID)
      );
      setLines(res.data.filter((l) => l && l.id && l.name));
    } catch {
      setLines([]);
    }
  }, []);

  useEffect(() => {
    void loadLines();
  }, [loadLines]);

  const lineNameById = useMemo(() => {
    const map: Record<string, string> = {};
    for (const l of lines) map[l.id] = l.name;
    return map;
  }, [lines]);

  const handleRefresh = useCallback(async () => {
    await Promise.allSettled([refreshAlerts(), refreshMessages()]);
  }, [refreshAlerts, refreshMessages]);

  const filteredAlerts = useMemo(() => {
    const q = normalizeText(searchTerm);
    if (!q) return alerts;
    return alerts.filter((a) =>
      normalizeText(`${a.title} ${a.description} ${a.alert_type}`).includes(q)
    );
  }, [alerts, searchTerm]);

  const filteredMessages = useMemo(() => {
    const q = normalizeText(searchTerm);
    if (!q) return messages;
    return messages.filter((m) =>
      normalizeText(`${m.title} ${m.description} ${m.status} ${m.priority}`).includes(q)
    );
  }, [messages, searchTerm]);

  const handleAlertSave = useCallback(
    async (payload: TransportAlertCreatePayload | TransportAlertUpdatePayload) => {
      let result: TransportAlertDTO | null;
      if (editingAlert) {
        result = await updateAlert(editingAlert.id, payload as TransportAlertUpdatePayload);
      } else {
        result = await createAlert(payload as TransportAlertCreatePayload);
      }
      if (result) {
        setShowAlertForm(false);
        setEditingAlert(null);
      }
    },
    [editingAlert, createAlert, updateAlert]
  );

  const handleMessageSave = useCallback(
    async (payload: OperatorMessageCreatePayload | OperatorMessageUpdatePayload) => {
      let result: OperatorMessageDTO | null;
      if (editingMessage) {
        result = await updateMessage(editingMessage.id, payload as OperatorMessageUpdatePayload);
      } else {
        result = await createMessage(payload as OperatorMessageCreatePayload);
      }
      if (result) {
        setShowMessageForm(false);
        setEditingMessage(null);
      }
    },
    [editingMessage, createMessage, updateMessage]
  );

  const handleDeactivateAlert = useCallback(
    async (id: string) => {
      const ok = await deactivateAlert(id);
      if (ok) setPendingDeactivateAlertId(null);
    },
    [deactivateAlert]
  );

  const handleDeleteAlert = useCallback(
    async (id: string) => {
      const ok = await removeAlert(id);
      if (ok) setPendingDeleteAlertId(null);
    },
    [removeAlert]
  );

  const handleCancelMessage = useCallback(
    async (id: string) => {
      const ok = await cancelMessage(id);
      if (ok) setPendingCancelMessageId(null);
    },
    [cancelMessage]
  );

  const handleDeleteMessage = useCallback(
    async (id: string) => {
      const ok = await removeMessage(id);
      if (ok) setPendingDeleteMessageId(null);
    },
    [removeMessage]
  );

  const openCreateAlert = useCallback(() => {
    setEditingAlert(null);
    setShowAlertForm(true);
  }, []);

  const closeAlertForm = useCallback(() => {
    setShowAlertForm(false);
    setEditingAlert(null);
  }, []);

  const openCreateMessage = useCallback(() => {
    setEditingMessage(null);
    setShowMessageForm(true);
  }, []);

  const closeMessageForm = useCallback(() => {
    setShowMessageForm(false);
    setEditingMessage(null);
  }, []);

  const alertFormInitial: AlertFormData = editingAlert
    ? {
        alert_type: editingAlert.alert_type,
        title: editingAlert.title,
        description: editingAlert.description,
        line_id: editingAlert.line_id ?? '',
        valid_from: isoToLocalDateTimeInput(editingAlert.valid_from),
        valid_until: isoToLocalDateTimeInput(editingAlert.valid_until),
        is_active: editingAlert.is_active,
      }
    : emptyAlertForm;

  const messageFormInitial: MessageFormData = editingMessage
    ? {
        title: editingMessage.title,
        description: editingMessage.description,
        priority: editingMessage.priority,
        line_id: editingMessage.line_id ?? '',
        publish_at: isoToLocalDateTimeInput(editingMessage.publish_at),
        expires_at: editingMessage.expires_at ? isoToLocalDateTimeInput(editingMessage.expires_at) : '',
      }
    : emptyMessageForm;

  const mutationError = activeSection === 'alerts' ? actionError : messagesActionError;

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <DashboardHeader
        title="Alertas y Mensajes"
        subtitle="Comunicación al público"
        actions={
          <div className="flex items-center gap-3">
            <RefreshButton onClick={() => void handleRefresh()} loading={loadingAlerts || loadingMessages} />
            {activeSection === 'alerts' ? (
              <Button variant="primary" onClick={openCreateAlert}>
                <Plus className="w-4 h-4" />
                Nueva Alerta
              </Button>
            ) : (
              <Button variant="primary" onClick={openCreateMessage}>
                <Plus className="w-4 h-4" />
                Nuevo Mensaje
              </Button>
            )}
          </div>
        }
      />

      <main className="p-4 sm:p-6 max-w-4xl mx-auto">
        <SectionTabs
          sections={[
            { key: 'alerts', label: 'Alertas' },
            { key: 'messages', label: 'Mensajes' },
          ]}
          activeSection={activeSection}
          onChange={setActiveSection}
        />

        {mutationError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {mutationError}
          </div>
        )}

        <div className="relative mb-4">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={activeSection === 'alerts'
              ? 'Buscar alerta por título, descripción o tipo...'
              : 'Buscar mensaje por título, descripción, estado o prioridad...'}
            className="w-full pl-9 pr-9 py-2 text-sm rounded-lg border border-slate-300 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
          />
          {searchTerm.length > 0 && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setSearchTerm('')}
              title="Limpiar búsqueda"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 rounded-full px-2 py-2"
            >
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>

        {activeSection === 'alerts' ? (
          <>
            {alertsError && (
              <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
                {alertsError}
              </div>
            )}

            {loadingAlerts ? (
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-10 text-center text-slate-500">
                Cargando alertas...
              </div>
            ) : filteredAlerts.length === 0 ? (
              <div className="bg-white rounded-xl border-2 border-dashed border-slate-200 p-8 text-center text-slate-400">
                {alerts.length === 0
                  ? 'No hay alertas registradas para este evento.'
                  : `No se encontraron alertas que coincidan con '${searchTerm.trim()}'.`}
              </div>
            ) : (
              <div className="space-y-3">
                {filteredAlerts.map((alert) => {
                  const status = getAlertStatus(alert);
                  return (
                    <div
                      key={alert.id}
                      className="rounded-xl border-2 border-slate-200 bg-white p-4 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3 min-w-0">
                          <Megaphone className="w-5 h-5 flex-shrink-0 mt-0.5 text-indigo-600" />
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-bold text-slate-800">{alert.title}</span>
                              <Badge variant={ALERT_TYPE_BADGES[alert.alert_type]}>
                                {ALERT_TYPE_LABELS[alert.alert_type] ?? alert.alert_type}
                              </Badge>
                              <Badge variant={status.variant}>{status.label}</Badge>
                            </div>
                            <p className="text-sm text-slate-600 mt-1 break-words">{alert.description}</p>
                            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-slate-500">
                              <span>Desde: {formatTimestamp(alert.valid_from)}</span>
                              <span>Hasta: {formatTimestamp(alert.valid_until)}</span>
                              {alert.line_id && (
                                <span>Línea: {lineNameById[alert.line_id] ?? alert.line_id}</span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          {alert.is_active && !isExpired(alert.valid_until) && (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => setPendingDeactivateAlertId(alert.id)}
                              disabled={saving}
                              title="Desactivar alerta"
                            >
                              <Power className="w-3.5 h-3.5" />
                              Desactivar
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => { setEditingAlert(alert); setShowAlertForm(true); }}
                            disabled={saving}
                          >
                            <Pencil className="w-3.5 h-3.5" />
                            Editar
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setPendingDeleteAlertId(alert.id)}
                            disabled={saving}
                            className="text-red-600 hover:bg-red-50"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            Eliminar
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        ) : (
          <>
            {messagesError && (
              <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
                {messagesError}
              </div>
            )}

            {loadingMessages ? (
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-10 text-center text-slate-500">
                Cargando mensajes...
              </div>
            ) : filteredMessages.length === 0 ? (
              <div className="bg-white rounded-xl border-2 border-dashed border-slate-200 p-8 text-center text-slate-400">
                {messages.length === 0
                  ? 'No hay mensajes registrados para este evento.'
                  : `No se encontraron mensajes que coincidan con '${searchTerm.trim()}'.`}
              </div>
            ) : (
              <div className="space-y-3">
                {filteredMessages.map((message) => (
                  <div
                    key={message.id}
                    className="rounded-xl border-2 border-slate-200 bg-white p-4 shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3 min-w-0">
                        <Ban className="w-5 h-5 flex-shrink-0 mt-0.5 text-indigo-600" />
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-slate-800">{message.title}</span>
                            <Badge variant={STATUS_BADGES[message.status]}>
                              {STATUS_LABELS[message.status] ?? message.status}
                            </Badge>
                            <Badge variant={PRIORITY_BADGES[message.priority]}>
                              {PRIORITY_LABELS[message.priority] ?? message.priority}
                            </Badge>
                          </div>
                          <p className="text-sm text-slate-600 mt-1 break-words">{message.description}</p>
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-slate-500">
                            <span>Publicar: {formatTimestamp(message.publish_at)}</span>
                            {message.expires_at && (
                              <span>Expira: {formatTimestamp(message.expires_at)}</span>
                            )}
                            {message.line_id && (
                              <span>Línea: {lineNameById[message.line_id] ?? message.line_id}</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        {message.status === 'draft' && (
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => void publishMessage(message.id)}
                            disabled={savingMessages}
                            title="Publicar mensaje"
                          >
                            Publicar
                          </Button>
                        )}
                        {message.status === 'published' && (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setPendingCancelMessageId(message.id)}
                            disabled={savingMessages}
                            title="Cancelar publicación"
                          >
                            <Ban className="w-3.5 h-3.5" />
                            Cancelar
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => { setEditingMessage(message); setShowMessageForm(true); }}
                          disabled={savingMessages || message.status === 'published'}
                        >
                          <Pencil className="w-3.5 h-3.5" />
                          Editar
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setPendingDeleteMessageId(message.id)}
                          disabled={savingMessages}
                          className="text-red-600 hover:bg-red-50"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          Eliminar
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </main>

      {showAlertForm && (
        <AlertFormModal
          initial={alertFormInitial}
          lines={lines}
          isEditing={!!editingAlert}
          onSave={handleAlertSave}
          onClose={closeAlertForm}
          saving={saving}
        />
      )}

      {showMessageForm && (
        <MessageFormModal
          initial={messageFormInitial}
          lines={lines}
          isEditing={!!editingMessage}
          onSave={handleMessageSave}
          onClose={closeMessageForm}
          saving={savingMessages}
        />
      )}

      <ConfirmDialog
        open={pendingDeactivateAlertId !== null}
        title="Desactivar alerta"
        message="¿Desactivar esta alerta? Dejará de mostrarse al público de forma inmediata."
        variant="primary"
        confirmLabel="Desactivar"
        onConfirm={() => { if (pendingDeactivateAlertId) void handleDeactivateAlert(pendingDeactivateAlertId); }}
        onCancel={() => setPendingDeactivateAlertId(null)}
      />

      <ConfirmDialog
        open={pendingDeleteAlertId !== null}
        title="Eliminar alerta"
        message="¿Eliminar esta alerta? Esta acción no se puede deshacer."
        confirmLabel="Eliminar"
        onConfirm={() => { if (pendingDeleteAlertId) void handleDeleteAlert(pendingDeleteAlertId); }}
        onCancel={() => setPendingDeleteAlertId(null)}
      />

      <ConfirmDialog
        open={pendingCancelMessageId !== null}
        title="Cancelar publicación"
        message="¿Cancelar este mensaje? Dejará de mostrarse al público de forma inmediata."
        variant="primary"
        confirmLabel="Cancelar mensaje"
        onConfirm={() => { if (pendingCancelMessageId) void handleCancelMessage(pendingCancelMessageId); }}
        onCancel={() => setPendingCancelMessageId(null)}
      />

      <ConfirmDialog
        open={pendingDeleteMessageId !== null}
        title="Eliminar mensaje"
        message="¿Eliminar este mensaje? Esta acción no se puede deshacer."
        confirmLabel="Eliminar"
        onConfirm={() => { if (pendingDeleteMessageId) void handleDeleteMessage(pendingDeleteMessageId); }}
        onCancel={() => setPendingDeleteMessageId(null)}
      />
    </div>
  );
}