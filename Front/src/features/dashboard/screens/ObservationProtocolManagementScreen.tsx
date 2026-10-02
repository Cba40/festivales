import { useCallback, useEffect, useMemo, useState } from 'react';
import { isAxiosError } from 'axios';
import { CheckCircle2, Pencil, Plus, Sparkles, Trash2 } from 'lucide-react';

import {
  applySuggestions,
  createProtocol,
  deleteProtocol,
  getSuggestions,
  listProtocols,
  updateProtocol,
  describeRule,
  INTERVAL_LABELS,
  INTERVAL_OPTIONS,
  METRIC_OPTIONS,
  THRESHOLD_OPTIONS,
  type ObservationProtocolDTO,
  type ProtocolSuggestionDTO,
  type TriggerMetric,
  type TriggerOperator,
} from '@/services/observationControlProtocolAdmin';
import { ComplianceAlertsPanel } from '@/components/ComplianceAlertsPanel';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import { Badge } from '@/features/dashboard/components/ui/Badge';
import { Card } from '@/features/dashboard/components/ui/Card';
import { Button } from '@/features/dashboard/components/ui/Button';
import { ConfirmDialog } from '@/features/dashboard/components/ui/ConfirmDialog';
import { RefreshButton } from '@/features/dashboard/components/ui';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'test-event-1';

interface ZoneTypeOption {
  id: string;
  name: string;
  slug: string;
}

interface EventDayOption {
  id: string;
  date: string;
  is_active: boolean;
}

type ModalState =
  | { mode: 'create' }
  | { mode: 'edit'; protocol: ObservationProtocolDTO }
  | null;

interface ProtocolForm {
  name: string;
  description: string;
  trigger_metric: TriggerMetric;
  trigger_operator: TriggerOperator;
  threshold_value: string;
  action_interval_minutes: number;
  zone_type_id: string;
  event_day_id: string;
  active: boolean;
}

function emptyForm(metric: TriggerMetric = 'saturation_level'): ProtocolForm {
  const opcion = THRESHOLD_OPTIONS[metric][1];
  return {
    name: '',
    description: '',
    trigger_metric: metric,
    trigger_operator: opcion.operator,
    threshold_value: opcion.value,
    action_interval_minutes: 5,
    zone_type_id: '',
    event_day_id: '',
    active: true,
  };
}

export function ObservationProtocolManagementScreen() {
  const [protocols, setProtocols] = useState<ObservationProtocolDTO[]>([]);
  const [suggestions, setSuggestions] = useState<ProtocolSuggestionDTO[]>([]);
  const [selectedSuggestions, setSelectedSuggestions] = useState<string[]>([]);
  const [zoneTypes, setZoneTypes] = useState<ZoneTypeOption[]>([]);
  const [eventDays, setEventDays] = useState<EventDayOption[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [showInactive, setShowInactive] = useState(false);

  const [modal, setModal] = useState<ModalState>(null);
  const [form, setForm] = useState<ProtocolForm>(emptyForm());
  const [modalSaving, setModalSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [referenceDataError, setReferenceDataError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setIsLoading(true);
    try {
      setProtocols(await listProtocols(EVENT_ID, showInactive));
      setError(null);
    } catch {
      setError('No se pudieron cargar los protocolos de observación.');
    } finally {
      setIsLoading(false);
    }
  }, [showInactive]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  useEffect(() => {
    let cancelado = false;
    // Las sugerencias vienen del backend (misma constante que usa el seed), asi
    // que la UI no puede proposes reglas que el seed no conhece.
    getSuggestions()
      .then((data) => {
        if (!cancelado) setSuggestions(data);
      })
      .catch(() => {
        if (!cancelado) setSuggestions([]);
      });
    return () => {
      cancelado = true;
    };
  }, []);

  useEffect(() => {
    let cancelado = false;
    // Antes: apiClient.get('/event-days?event_id=...') → 404. La ruta real es
    // /api/events/{event_id}/event-days (app/api/routes/event_days.py:40) y
    // apiClient ya antepone /api, asi que lo correcto es usar el helper de
    // endpoints en vez de escribir la URL a mano.
    apiClient
      .get<EventDayOption[]>(endpoints.eventDays.list(EVENT_ID))
      .then((res) => {
        if (cancelado) return;
        setEventDays(res.data ?? []);
        setReferenceDataError(null);
      })
      .catch(() => {
        if (cancelado) return;
        setEventDays([]);
        // Sin este aviso el dropdown "Jornadas" queda con la unica opcion
        // "Todas las jornadas" y el operador no tiene forma de saber que le
        // falta cargar el catalogo: pareceria que el evento no tiene jornadas.
        setReferenceDataError(
          'No se pudieron cargar las jornadas del evento. No vas a poder acotar una regla a una jornada.'
        );
      });
    return () => {
      cancelado = true;
    };
  }, []);

  useEffect(() => {
    let cancelado = false;
    apiClient
      .get<ZoneTypeOption[]>(endpoints.contextEngine.zoneTypes())
      .then((res) => {
        if (cancelado) return;
        setZoneTypes(res.data ?? []);
        setReferenceDataError(null);
      })
      .catch(() => {
        if (cancelado) return;
        setZoneTypes([]);
        setReferenceDataError(
          'No se pudieron cargar los tipos de zona. Las reglas se van a aplicar a todas las zonas.'
        );
      });
    return () => {
      cancelado = true;
    };
  }, []);

  const preview = useMemo(
    () =>
      describeRule({
        trigger_metric: form.trigger_metric,
        trigger_operator: form.trigger_operator,
        threshold_value: form.threshold_value,
        action_interval_minutes: form.action_interval_minutes,
      }),
    [form.trigger_metric, form.trigger_operator, form.threshold_value, form.action_interval_minutes]
  );

  const handleMetricChange = (metric: TriggerMetric) => {
    // Cambiar la métrica invalida el umbral elegido: cada una tiene su escala
    // (0..1 vs minutos vs personas). Se resetea al valor por defecto de esa métrica.
    const opcion = THRESHOLD_OPTIONS[metric][1];
    setForm((prev) => ({
      ...prev,
      trigger_metric: metric,
      trigger_operator: opcion.operator,
      threshold_value: opcion.value,
    }));
  };

  const handleThresholdChange = (index: number) => {
    const opcion = THRESHOLD_OPTIONS[form.trigger_metric][index];
    if (!opcion) return;
    setForm((prev) => ({
      ...prev,
      trigger_operator: opcion.operator,
      threshold_value: opcion.value,
    }));
  };

  const openCreate = () => {
    setForm(emptyForm());
    setModalError(null);
    setModal({ mode: 'create' });
  };

  const openEdit = (protocol: ObservationProtocolDTO) => {
    setForm({
      name: protocol.name,
      description: protocol.description ?? '',
      trigger_metric: protocol.trigger_metric,
      trigger_operator: protocol.trigger_operator,
      threshold_value: protocol.threshold_value,
      action_interval_minutes: protocol.action_interval_minutes,
      zone_type_id: protocol.zone_type_id ?? '',
      event_day_id: protocol.event_day_id ?? '',
      active: protocol.active,
    });
    setModalError(null);
    setModal({ mode: 'edit', protocol });
  };

  const handleSubmit = useCallback(async () => {
    if (form.name.trim() === '') {
      setModalError('Poné un nombre para la regla.');
      return;
    }
    setModalSaving(true);
    setModalError(null);
    const payload = {
      name: form.name.trim(),
      description: form.description.trim() === '' ? null : form.description.trim(),
      trigger_metric: form.trigger_metric,
      trigger_operator: form.trigger_operator,
      threshold_value: form.threshold_value,
      action_interval_minutes: Number(form.action_interval_minutes),
      zone_type_id: form.zone_type_id === '' ? null : form.zone_type_id,
      event_day_id: form.event_day_id === '' ? null : form.event_day_id,
      active: form.active,
    };
    try {
      if (modal?.mode === 'edit') {
        await updateProtocol(modal.protocol.id, payload);
        setResult('Protocolo actualizado.');
      } else {
        await createProtocol({ event_id: EVENT_ID, order: protocols.length, ...payload });
        setResult('Protocolo creado.');
      }
      setModal(null);
      await cargar();
    } catch (err) {
      setModalError(detalleDeError(err, 'No se pudo guardar el protocolo.'));
    } finally {
      setModalSaving(false);
    }
  }, [form, modal, protocols.length, cargar]);

  const handleApplySuggestions = useCallback(async () => {
    if (selectedSuggestions.length === 0) return;
    setApplying(true);
    try {
      const res = await applySuggestions(EVENT_ID, selectedSuggestions);
      setResult(
        `Se crearon ${res.created} protocolo(s)` +
          (res.skipped > 0 ? ` y ${res.skipped} ya existían.` : '.')
      );
      setSelectedSuggestions([]);
      await cargar();
    } catch (err) {
      setError(detalleDeError(err, 'No se pudieron aplicar las sugerencias.'));
    } finally {
      setApplying(false);
    }
  }, [selectedSuggestions, cargar]);

  const handleConfirmDelete = useCallback(async () => {
    if (!pendingDeleteId) return;
    try {
      await deleteProtocol(pendingDeleteId);
      setResult('Protocolo desactivado.');
      setPendingDeleteId(null);
      await cargar();
    } catch {
      setError('No se pudo desactivar el protocolo.');
    }
  }, [pendingDeleteId, cargar]);

  return (
    <main className="max-w-5xl mx-auto space-y-6">
      <div className="flex justify-end">
        <RefreshButton onClick={() => void cargar()} loading={isLoading} />
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}
      {result && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
          {result}
        </div>
      )}
      {referenceDataError && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
          {referenceDataError}
        </div>
      )}

      <ComplianceAlertsPanel eventId={EVENT_ID} />

      {suggestions.length > 0 && (
        <Card variant="standard">
          <h2 className="font-bold text-slate-800 mb-1">Sugerencias</h2>
          <p className="text-xs text-slate-500 mb-3">
            Reglas típicas para una jornada. Adoptarlas crea protocolos editables;
            después podés ajustarlos o desactivarlos.
          </p>
          <ul className="space-y-2">
            {suggestions.map((s) => (
              <li key={s.key}>
                <label className="flex items-start gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={selectedSuggestions.includes(s.key)}
                    onChange={(e) =>
                      setSelectedSuggestions((prev) =>
                        e.target.checked
                          ? [...prev, s.key]
                          : prev.filter((k) => k !== s.key)
                      )
                    }
                  />
                  <span>
                    <span className="text-sm font-medium text-slate-800">{s.name}</span>
                    <span className="block text-xs text-slate-500">{s.rule_sentence}</span>
                  </span>
                </label>
              </li>
            ))}
          </ul>
          <Button
            className="mt-4"
            onClick={() => void handleApplySuggestions()}
            disabled={applying || selectedSuggestions.length === 0}
          >
            <Sparkles className="w-4 h-4" />
            {applying
              ? 'Aplicando...'
              : `Aplicar ${selectedSuggestions.length || ''} sugerencia(s)`}
          </Button>
        </Card>
      )}

      <Card variant="standard">
        <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
          <h2 className="font-bold text-slate-800">
            Protocolos de observación ({protocols.length})
          </h2>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={showInactive}
                onChange={(e) => setShowInactive(e.target.checked)}
              />
              Ver desactivados
            </label>
            <Button onClick={openCreate}>
              <Plus className="w-4 h-4" />
              Nuevo protocolo
            </Button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="px-5 py-2 font-medium">Nombre</th>
                <th className="px-5 py-2 font-medium">Regla</th>
                <th className="px-5 py-2 font-medium">Frecuencia</th>
                <th className="px-5 py-2 font-medium">Alcance</th>
                <th className="px-5 py-2 font-medium text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {protocols.length === 0 && !isLoading && (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-slate-400 italic">
                    Todavía no hay protocolos de observación para este evento.
                  </td>
                </tr>
              )}
              {protocols.map((p) => (
                <tr key={p.id} className="border-b border-slate-100 align-top">
                  <td className="px-5 py-2 text-slate-700">
                    <div>{p.name}</div>
                    {!p.active && (
                      <Badge variant="neutral" className="mt-1">
                        Desactivado
                      </Badge>
                    )}
                  </td>
                  <td className="px-5 py-2 text-slate-600">
                    {describeRule({
                      trigger_metric: p.trigger_metric,
                      trigger_operator: p.trigger_operator,
                      threshold_value: p.threshold_value,
                      action_interval_minutes: p.action_interval_minutes,
                    })}
                  </td>
                  <td className="px-5 py-2 text-slate-600">
                    {INTERVAL_LABELS[p.action_interval_minutes] ??
                      `cada ${p.action_interval_minutes} min`}
                  </td>
                  <td className="px-5 py-2 text-slate-600">
                    {p.zone_type_id
                      ? zoneTypes.find((z) => z.id === p.zone_type_id)?.name ??
                        'Tipo de zona'
                      : 'Todas las zonas'}
                    {p.event_day_id ? (
                      <div className="text-xs text-slate-400">
                        Jornada {eventDays.find((d) => d.id === p.event_day_id)?.date ?? ''}
                      </div>
                    ) : (
                      <div className="text-xs text-slate-400">Todas las jornadas</div>
                    )}
                  </td>
                  <td className="px-5 py-2 text-right">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(p)}>
                      <Pencil className="w-3 h-3" />
                      Editar
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setPendingDeleteId(p.id)}>
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-5 border-b border-slate-200">
              <h3 className="font-semibold text-slate-800">
                {modal.mode === 'edit' ? 'Editar protocolo' : 'Nuevo protocolo'}
              </h3>
            </div>

            <div className="p-5 space-y-4">
              <label className="block text-sm">
                <span className="text-slate-700 font-medium">Nombre</span>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Ej: Saturación alta"
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </label>

              <label className="block text-sm">
                <span className="text-slate-700 font-medium">Se activa cuando</span>
                <select
                  value={form.trigger_metric}
                  onChange={(e) => handleMetricChange(e.target.value as TriggerMetric)}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {METRIC_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block text-sm">
                <span className="text-slate-700 font-medium">Umbral</span>
                <select
                  value={`${form.trigger_operator}|${form.threshold_value}`}
                  onChange={(e) =>
                    handleThresholdChange(
                      THRESHOLD_OPTIONS[form.trigger_metric].findIndex(
                        (o) => `${o.operator}|${o.value}` === e.target.value
                      )
                    )
                  }
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {THRESHOLD_OPTIONS[form.trigger_metric].map((o) => (
                    <option key={`${o.operator}|${o.value}`} value={`${o.operator}|${o.value}`}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block text-sm">
                <span className="text-slate-700 font-medium">Registrar</span>
                <select
                  value={form.action_interval_minutes}
                  onChange={(e) =>
                    setForm({ ...form, action_interval_minutes: Number(e.target.value) })
                  }
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {INTERVAL_OPTIONS.map((i) => (
                    <option key={i} value={i}>
                      {INTERVAL_LABELS[i]}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block text-sm">
                <span className="text-slate-700 font-medium">Zonas</span>
                <select
                  value={form.zone_type_id}
                  onChange={(e) => setForm({ ...form, zone_type_id: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Todas las zonas</option>
                  {zoneTypes.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block text-sm">
                <span className="text-slate-700 font-medium">Jornadas</span>
                <select
                  value={form.event_day_id}
                  onChange={(e) => setForm({ ...form, event_day_id: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Todas las jornadas</option>
                  {eventDays.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.date}
                      {d.is_active ? ' (hoy)' : ''}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block text-sm">
                <span className="text-slate-700 font-medium">Descripción (opcional)</span>
                <input
                  type="text"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </label>

              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={form.active}
                  onChange={(e) => setForm({ ...form, active: e.target.checked })}
                />
                Activo
              </label>

              {/* Preview: la regla escrita como la va a entender el operador,
                  sin que tenga que cruzarla con la tabla de enums. */}
              <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-lg text-sm text-indigo-900">
                <span className="font-medium">Resultado: </span>
                {preview}
              </div>

              {modalError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  {modalError}
                </div>
              )}
            </div>

            <div className="p-5 border-t border-slate-200 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setModal(null)}>
                Cancelar
              </Button>
              <Button onClick={() => void handleSubmit()} disabled={modalSaving}>
                <CheckCircle2 className="w-4 h-4" />
                {modalSaving ? 'Guardando...' : 'Guardar'}
              </Button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={pendingDeleteId !== null}
        title="Desactivar protocolo"
        message="El protocolo va a dejar de evaluarse. Se conserva en la base para el histórico."
        confirmLabel="Desactivar"
        onConfirm={() => void handleConfirmDelete()}
        onCancel={() => setPendingDeleteId(null)}
      />
    </main>
  );
}

/** Traduce el detalle de FastAPI a algo entendible para el operador. */
function detalleDeError(err: unknown, porDefecto: string): string {
  if (isAxiosError(err)) {
    const detalle = err.response?.data?.detail;
    if (typeof detalle === 'string') return detalle;
    if (Array.isArray(detalle) && detalle.length > 0) {
      const primero = detalle[0];
      if (typeof primero?.msg === 'string') return primero.msg;
    }
    if (err.response?.status === 409) {
      return 'Ya existe un protocolo con ese nombre para este evento.';
    }
  }
  return porDefecto;
}