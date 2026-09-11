import { useCallback, useEffect, useState } from 'react';
import { isAxiosError } from 'axios';
import { Plus, Pencil, Trash2, ArrowUp, ArrowDown, X, AlertTriangle, Shield, Heart, Ambulance, Flame, ClipboardList, RefreshCw } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import {
  getProtocols,
  createProtocol,
  updateProtocol,
  deleteProtocol,
  type ProtocolContext,
  type ProtocolDTO,
} from '../../../services/emergencyProtocolAdmin';
import { EMERGENCY_TYPE_LABELS, type EmergencyType } from '../constants/emergencyLabels';
import { Badge, type BadgeVariant } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';

type ContextFilter = ProtocolContext | 'todos';

type ModalState =
  | { mode: 'create' }
  | { mode: 'edit'; protocol: ProtocolDTO }
  | null;

interface ProtocolForm {
  context: ProtocolContext;
  title: string;
  description: string;
  icon: string;
  steps: string[];
  priority: string;
  order: string;
  target_type: EmergencyType | '';
  active: boolean;
}

const CONTEXT_OPTIONS: { key: ProtocolContext; label: string; badgeVariant: BadgeVariant }[] = [
  { key: 'festival', label: 'Festival', badgeVariant: 'info' },
  { key: 'transporte', label: 'Transporte', badgeVariant: 'success' },
  { key: 'hospedaje', label: 'Hospedaje', badgeVariant: 'warning' },
];

const PRIORITY_OPTIONS = [
  { value: '1', label: 'Alta' },
  { value: '2', label: 'Media' },
  { value: '3', label: 'Baja' },
];

const PRIORITY_LABELS: Record<string, string> = {
  '1': 'Alta',
  '2': 'Media',
  '3': 'Baja',
};

const PRIORITY_BADGE_VARIANTS: Record<string, BadgeVariant> = {
  '1': 'error',
  '2': 'warning',
  '3': 'neutral',
};

const PROTOCOL_ICON_OPTIONS: { value: string; icon: LucideIcon; label: string }[] = [
  { value: '🚨', icon: AlertTriangle, label: 'Alerta' },
  { value: '🚑', icon: Ambulance, label: 'Ambulancia' },
  { value: '🚒', icon: Flame, label: 'Bomberos' },
  { value: '👮', icon: Shield, label: 'Seguridad' },
  { value: '🏥', icon: Heart, label: 'Salud' },
  { value: '📋', icon: ClipboardList, label: 'Documento' },
];

const PROTOCOL_ICON_MAP: Record<string, LucideIcon> = Object.fromEntries(
  PROTOCOL_ICON_OPTIONS.map((o) => [o.value, o.icon])
);

const emptyForm: ProtocolForm = {
  context: 'festival',
  title: '',
  description: '',
  icon: '📋',
  steps: [''],
  priority: '1',
  order: '0',
  target_type: '',
  active: true,
};

export function ProtocolManagementScreen() {
  const [activeContext, setActiveContext] = useState<ContextFilter>('festival');
  const [protocols, setProtocols] = useState<ProtocolDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const [modal, setModal] = useState<ModalState>(null);
  const [form, setForm] = useState<ProtocolForm>(emptyForm);
  const [modalSaving, setModalSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [showInactive, setShowInactive] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const cargar = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getProtocols(
        activeContext === 'todos' ? undefined : activeContext,
        showInactive
      );
      setProtocols(data);
      setError(null);
    } catch {
      setError('No se pudieron cargar los protocolos.');
    } finally {
      setLoading(false);
    }
  }, [activeContext, showInactive]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await cargar();
    } finally {
      setRefreshing(false);
    }
  };

  const setCampo = <K extends keyof ProtocolForm>(campo: K, valor: ProtocolForm[K]) => {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  };

  const setStep = (index: number, valor: string) => {
    setForm((prev) => ({
      ...prev,
      steps: prev.steps.map((s, i) => (i === index ? valor : s)),
    }));
  };

  const addStep = () => {
    setForm((prev) => ({ ...prev, steps: [...prev.steps, ''] }));
  };

  const removeStep = (index: number) => {
    setForm((prev) => ({
      ...prev,
      steps: prev.steps.filter((_, i) => i !== index),
    }));
  };

  const moveStep = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= form.steps.length) return;
    setForm((prev) => {
      const next = [...prev.steps];
      const [item] = next.splice(index, 1);
      next.splice(target, 0, item);
      return { ...prev, steps: next };
    });
  };

  const abrirCrear = () => {
    setForm({
      ...emptyForm,
      context: activeContext === 'todos' ? 'festival' : activeContext,
    });
    setModalError(null);
    setModal({ mode: 'create' });
  };

  const abrirEditar = (p: ProtocolDTO) => {
    setForm({
      context: p.context,
      title: p.title,
      description: p.description ?? '',
      icon: p.icon,
      steps: p.steps.length > 0 ? [...p.steps] : [''],
      priority: String(p.priority),
      order: String(p.order),
      target_type: p.target_type ?? '',
      active: p.active,
    });
    setModalError(null);
    setModal({ mode: 'edit', protocol: p });
  };

  const guardar = async () => {
    const title = form.title.trim();
    if (!title) {
      setModalError('El título es obligatorio.');
      return;
    }
    if (!form.icon.trim()) {
      setModalError('El ícono es obligatorio.');
      return;
    }
    setModalSaving(true);
    setModalError(null);
    try {
      const payload = {
        context: form.context,
        title,
        description: form.description.trim() || null,
        icon: form.icon.trim(),
        steps: form.steps.map((s) => s.trim()),
        priority: Number(form.priority),
        order: Number(form.order) || 0,
        target_type: form.target_type === '' ? null : form.target_type,
        active: form.active,
      };
      if (modal?.mode === 'edit') {
        await updateProtocol(modal.protocol.id, payload);
        setResult('Protocolo actualizado.');
      } else {
        await createProtocol(payload);
        setResult(`Protocolo "${title}" creado.`);
      }
      setModal(null);
      await cargar();
    } catch (err) {
      const status = isAxiosError(err) ? err.response?.status : undefined;
      if (status === 409) {
        setModalError('Ya existe un protocolo con ese título en este contexto.');
      } else {
        setModalError('No se pudo guardar el protocolo.');
      }
    } finally {
      setModalSaving(false);
    }
  };

  const alternarActivo = async (p: ProtocolDTO) => {
    try {
      await updateProtocol(p.id, { active: !p.active });
      setResult(p.active ? 'Protocolo desactivado.' : 'Protocolo activado.');
      await cargar();
    } catch {
      setError('No se pudo actualizar el estado del protocolo.');
    }
  };

  const eliminar = async (p: ProtocolDTO) => {
    try {
      await deleteProtocol(p.id);
      setResult('Protocolo desactivado.');
      await cargar();
    } catch {
      setError('No se pudo desactivar el protocolo.');
    }
  };

  const handleDeleteConfirm = async () => {
    if (!pendingDeleteId) return;
    const p = protocols.find((pr) => pr.id === pendingDeleteId);
    if (!p) return;
    await eliminar(p);
    setPendingDeleteId(null);
  };

  const labelContexto = (context: ProtocolContext) =>
    CONTEXT_OPTIONS.find((c) => c.key === context)?.label ?? context;

  const badgeVariantContexto = (context: ProtocolContext) =>
    CONTEXT_OPTIONS.find((c) => c.key === context)?.badgeVariant ?? 'neutral';

  const inputCls = 'w-full border-slate-300 rounded-md py-2 px-3 focus:ring-indigo-500 focus:border-indigo-500';

  return (
    <div className="space-y-10">
      <section>
        <div className="flex justify-between items-center mb-4 gap-3 flex-wrap">
          <h2 className="text-lg font-semibold text-slate-700">
            Protocolos de Emergencia ({protocols.length})
          </h2>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex gap-1">
              <button
                onClick={() => setActiveContext('todos')}
                className={`text-sm font-medium px-3 py-1.5 rounded-md transition-colors ${
                  activeContext === 'todos'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                }`}
              >
                Todos
              </button>
              {CONTEXT_OPTIONS.map((c) => (
                <button
                  key={c.key}
                  onClick={() => setActiveContext(c.key)}
                  className={`text-sm font-medium px-3 py-1.5 rounded-md transition-colors ${
                    activeContext === c.key
                      ? 'bg-indigo-600 text-white'
                      : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
            <Button variant="secondary" size="sm" onClick={() => void handleRefresh()} disabled={refreshing}>
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              {refreshing ? 'Actualizando...' : 'Actualizar'}
            </Button>
            <Button variant="primary" onClick={abrirCrear}>
              <Plus className="w-4 h-4" />
              Nuevo Protocolo
            </Button>
          </div>
        </div>

        {result && (
          <p className="mb-4 text-sm text-green-700 bg-green-50 border border-green-200 rounded-md p-3">
            {result}
          </p>
        )}

        <div className="flex items-center justify-end gap-2 mb-4">
          <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="h-4 w-4 rounded accent-indigo-600"
            />
            Mostrar inactivos
          </label>
          {showInactive && protocols.some((p) => !p.active) && (
            <Badge variant="neutral">
              {protocols.filter((p) => !p.active).length} inactivos
            </Badge>
          )}
        </div>

        {loading ? (
          <p className="text-sm text-slate-500 italic">Cargando protocolos...</p>
        ) : error ? (
          <div className="mb-4 flex items-center justify-between gap-3 p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
            <span>{error}</span>
            <button
              type="button"
              onClick={() => void cargar()}
              className="whitespace-nowrap underline font-medium"
            >
              Reintentar
            </button>
          </div>
        ) : protocols.length === 0 ? (
          <p className="text-sm text-slate-500 italic text-center py-8 bg-white border border-slate-200 rounded-lg">
            No hay protocolos{activeContext !== 'todos' ? ` de ${labelContexto(activeContext)}` : ''}.
            Creá el primero con "+ Nuevo Protocolo".
          </p>
        ) : (
<div className="bg-white rounded-lg border border-slate-200 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-slate-500">
                    <th className="px-4 py-3 font-medium">Ícono</th>
                    <th className="px-4 py-3 font-medium">Título</th>
                    <th className="px-4 py-3 font-medium">Contexto</th>
                    <th className="px-4 py-3 font-medium">Target Type</th>
                    <th className="px-4 py-3 font-medium">Prioridad</th>
                    <th className="px-4 py-3 font-medium">Orden</th>
                    <th className="px-4 py-3 font-medium">Estado</th>
                    <th className="px-4 py-3 font-medium text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {protocols.map((p) => {
                    const Icon = PROTOCOL_ICON_MAP[p.icon] ?? AlertTriangle;
                    return (
                      <tr key={p.id}>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600">
                            <Icon className="w-4 h-4" />
                          </span>
                        </td>
                        <td className="px-4 py-3 font-medium text-slate-800">{p.title}</td>
                        <td className="px-4 py-3">
                          <Badge variant={badgeVariantContexto(p.context)}>
                            {labelContexto(p.context)}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          {p.target_type ? EMERGENCY_TYPE_LABELS[p.target_type] : '—'}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={PRIORITY_BADGE_VARIANTS[String(p.priority)] ?? 'neutral'}>
                            {PRIORITY_LABELS[String(p.priority)] ?? String(p.priority)}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-slate-600">{p.order}</td>
                        <td className="px-4 py-3">
                          {p.active ? (
                            <Badge variant="success">Activo</Badge>
                          ) : (
                            <Badge variant="neutral">Inactivo</Badge>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => abrirEditar(p)}
                              title="Editar"
                              className="mr-1"
                            >
                              <Pencil className="w-3.5 h-3.5" />
                              Editar
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => void alternarActivo(p)}
                              title={p.active ? 'Desactivar' : 'Activar'}
                            >
                              {p.active ? 'Desactivar' : 'Activar'}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setPendingDeleteId(p.id)}
                              title="Eliminar"
                              className="text-red-600 hover:bg-red-50"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              Eliminar
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
        )}
      </section>

      {modal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50">
          <Card
            variant="standard"
            className="w-full max-w-2xl mx-4 space-y-4 max-h-[90vh] overflow-y-auto"
          >
            <h3 className="text-lg font-semibold text-slate-800">
              {modal.mode === 'create' ? 'Nuevo Protocolo' : 'Editar Protocolo'}
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Contexto *</label>
                <select
                  value={form.context}
                  onChange={(e) => setCampo('context', e.target.value as ProtocolContext)}
                  className={inputCls}
                >
                  {CONTEXT_OPTIONS.map((c) => (
                    <option key={c.key} value={c.key}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Ícono *</label>
                <div className="flex flex-wrap gap-2">
                  {PROTOCOL_ICON_OPTIONS.map((opt) => {
                    const OptionIcon = opt.icon;
                    const selected = form.icon === opt.value;
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setCampo('icon', opt.value)}
                        title={opt.label}
                        aria-label={opt.label}
                        className={`flex items-center justify-center w-10 h-10 rounded-lg border transition-colors ${
                          selected
                            ? 'bg-indigo-600 text-white border-indigo-600'
                            : 'bg-white text-slate-600 border-slate-300 hover:border-indigo-400 hover:bg-indigo-50'
                        }`}
                      >
                        <OptionIcon className="w-4 h-4" />
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Título *</label>
                <input
                  type="text"
                  value={form.title}
                  onChange={(e) => setCampo('title', e.target.value)}
                  placeholder="Ej: Niño perdido"
                  className={inputCls}
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Descripción</label>
                <input
                  type="text"
                  value={form.description}
                  onChange={(e) => setCampo('description', e.target.value)}
                  placeholder="Qué situación cubre este protocolo"
                  className={inputCls}
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Pasos a seguir
                </label>
                <div className="space-y-2">
                  {form.steps.map((step, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <div className="flex flex-col">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => moveStep(i, -1)}
                          disabled={i === 0}
                          aria-label="Subir paso"
                          className="px-1 py-0.5"
                        >
                          <ArrowUp className="w-3.5 h-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => moveStep(i, 1)}
                          disabled={i === form.steps.length - 1}
                          aria-label="Bajar paso"
                          className="px-1 py-0.5"
                        >
                          <ArrowDown className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                      <input
                        type="text"
                        value={step}
                        onChange={(e) => setStep(i, e.target.value)}
                        placeholder={`Paso ${i + 1}: qué debe hacer el usuario`}
                        className={inputCls}
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeStep(i)}
                        aria-label="Eliminar paso"
                        className="text-red-600 hover:bg-red-50"
                      >
                        <X className="w-3.5 h-3.5" />
                        Eliminar
                      </Button>
                    </div>
                  ))}
                  <Button variant="ghost" size="sm" onClick={addStep}>
                    <Plus className="w-3.5 h-3.5" />
                    Agregar paso
                  </Button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Prioridad</label>
                <select
                  value={form.priority}
                  onChange={(e) => setCampo('priority', e.target.value)}
                  className={inputCls}
                >
                  {PRIORITY_OPTIONS.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Orden</label>
                <input
                  type="number"
                  min={0}
                  value={form.order}
                  onChange={(e) => setCampo('order', e.target.value)}
                  className={inputCls}
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Target Type (recurso territorial vinculado)
                </label>
                <select
                  value={form.target_type}
                  onChange={(e) => setCampo('target_type', e.target.value as EmergencyType | '')}
                  className={inputCls}
                >
                  <option value="">Ninguno</option>
                  {(Object.keys(EMERGENCY_TYPE_LABELS) as EmergencyType[]).map((t) => (
                    <option key={t} value={t}>
                      {EMERGENCY_TYPE_LABELS[t]}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={form.active}
                onChange={(e) => setCampo('active', e.target.checked)}
                className="accent-indigo-600"
              />
              Activo (visible en la pantalla "Emergencias")
            </label>

            {modalError && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
                {modalError}
              </p>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" onClick={() => setModal(null)}>
                Cancelar
              </Button>
              <Button
                variant="primary"
                onClick={() => void guardar()}
                disabled={modalSaving}
              >
                {modalSaving ? 'Guardando...' : 'Guardar'}
              </Button>
            </div>
          </Card>
        </div>
      )}

      <ConfirmDialog
        open={pendingDeleteId !== null}
        title="Eliminar protocolo"
        message={`¿Desactivar el protocolo "${protocols.find((p) => p.id === pendingDeleteId)?.title ?? ''}"? Se dejará de mostrar en la app pública. Esta acción no se puede deshacer.`}
        confirmLabel="Eliminar"
        cancelLabel="Cancelar"
        variant="destructive"
        onConfirm={() => void handleDeleteConfirm()}
        onCancel={() => setPendingDeleteId(null)}
      />
    </div>
  );
}