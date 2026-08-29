import { useCallback, useEffect, useState } from 'react';
import { isAxiosError } from 'axios';
import {
  getProtocols,
  createProtocol,
  updateProtocol,
  deleteProtocol,
  type ProtocolContext,
  type ProtocolDTO,
} from '../../../services/emergencyProtocolAdmin';
import type { EmergencyType } from '../../../services/emergencyAdmin';

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
  target_type: string;
  active: boolean;
}

const CONTEXT_OPTIONS: { key: ProtocolContext; label: string; badge: string }[] = [
  { key: 'festival', label: 'Festival', badge: 'bg-violet-100 text-violet-700' },
  { key: 'transporte', label: 'Transporte', badge: 'bg-sky-100 text-sky-700' },
  { key: 'hospedaje', label: 'Hospedaje', badge: 'bg-amber-100 text-amber-700' },
];

const PRIORITY_OPTIONS = [
  { value: '1', label: '1 · Crítica' },
  { value: '2', label: '2 · Alta' },
  { value: '3', label: '3 · Media' },
];

const TYPE_LABELS: Record<EmergencyType, string> = {
  policia: 'Policía',
  bomberos: 'Bomberos',
  salud: 'Salud',
  defensa_civil: 'Defensa Civil',
  numero_emergencia: 'Número de Emergencia',
  otro: 'Otro',
};

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

  const cargar = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getProtocols(activeContext === 'todos' ? undefined : activeContext);
      setProtocols(data);
      setError(null);
    } catch {
      setError('No se pudieron cargar los protocolos.');
    } finally {
      setLoading(false);
    }
  }, [activeContext]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

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
    const confirmado = window.confirm(
      `¿Desactivar el protocolo "${p.title}"? Se dejará de mostrar en la app pública. Esta acción no se puede deshacer.`
    );
    if (!confirmado) return;
    try {
      await deleteProtocol(p.id);
      setResult('Protocolo desactivado.');
      await cargar();
    } catch {
      setError('No se pudo desactivar el protocolo.');
    }
  };

  const labelContexto = (context: ProtocolContext) =>
    CONTEXT_OPTIONS.find((c) => c.key === context)?.label ?? context;

  const badgeContexto = (context: ProtocolContext) =>
    CONTEXT_OPTIONS.find((c) => c.key === context)?.badge ?? 'bg-slate-100 text-slate-700';

  const inputCls = 'w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500';

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
                    ? 'bg-slate-800 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
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
                      ? 'bg-slate-800 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
            <button
              onClick={abrirCrear}
              className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md text-sm font-medium transition-colors"
            >
              + Nuevo Protocolo
            </button>
          </div>
        </div>

        {result && (
          <p className="mb-4 text-sm text-green-700 bg-green-50 border border-green-200 rounded-md p-3">
            {result}
          </p>
        )}

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
                {protocols.map((p) => (
                  <tr key={p.id}>
                    <td className="px-4 py-3 text-xl">{p.icon}</td>
                    <td className="px-4 py-3 font-medium text-slate-800">{p.title}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${badgeContexto(p.context)}`}
                      >
                        {labelContexto(p.context)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {p.target_type ? TYPE_LABELS[p.target_type] : '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{p.priority}</td>
                    <td className="px-4 py-3 text-slate-600">{p.order}</td>
                    <td className="px-4 py-3">
                      {p.active ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">
                          Activo
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-200 text-slate-600">
                          Inactivo
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1">
                        <button
                          onClick={() => abrirEditar(p)}
                          className="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md transition-colors"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => void alternarActivo(p)}
                          className="text-sm text-slate-600 hover:bg-slate-100 px-3 py-1.5 rounded-md transition-colors"
                        >
                          {p.active ? 'Desactivar' : 'Activar'}
                        </button>
                        <button
                          onClick={() => void eliminar(p)}
                          className="text-sm text-red-600 hover:bg-red-50 px-3 py-1.5 rounded-md transition-colors"
                        >
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {modal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6 mx-4 space-y-4 max-h-[90vh] overflow-y-auto">
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
                <label className="block text-sm font-medium text-slate-700 mb-1">Ícono</label>
                <input
                  type="text"
                  value={form.icon}
                  onChange={(e) => setCampo('icon', e.target.value)}
                  placeholder="Ej: 🚨"
                  className={inputCls}
                />
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
                        <button
                          type="button"
                          onClick={() => moveStep(i, -1)}
                          disabled={i === 0}
                          className="text-slate-500 hover:text-slate-800 disabled:opacity-30 text-xs leading-none px-1"
                          aria-label="Subir paso"
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          onClick={() => moveStep(i, 1)}
                          disabled={i === form.steps.length - 1}
                          className="text-slate-500 hover:text-slate-800 disabled:opacity-30 text-xs leading-none px-1"
                          aria-label="Bajar paso"
                        >
                          ↓
                        </button>
                      </div>
                      <input
                        type="text"
                        value={step}
                        onChange={(e) => setStep(i, e.target.value)}
                        placeholder={`Paso ${i + 1}: qué debe hacer el usuario`}
                        className={inputCls}
                      />
                      <button
                        type="button"
                        onClick={() => removeStep(i)}
                        className="text-red-500 hover:bg-red-50 rounded-md px-2 py-1.5 transition-colors"
                        aria-label="Eliminar paso"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={addStep}
                    className="text-sm font-medium text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md transition-colors"
                  >
                    + Agregar paso
                  </button>
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
                  onChange={(e) => setCampo('target_type', e.target.value)}
                  className={inputCls}
                >
                  <option value="">Ninguno</option>
                  {(Object.keys(TYPE_LABELS) as EmergencyType[]).map((t) => (
                    <option key={t} value={t}>
                      {TYPE_LABELS[t]}
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
                className="accent-emerald-600"
              />
              Activo (visible en la pantalla "Emergencias")
            </label>

            {modalError && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
                {modalError}
              </p>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setModal(null)}
                className="py-2 px-4 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => void guardar()}
                disabled={modalSaving}
                className="py-2 px-4 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md transition-colors"
              >
                {modalSaving ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}