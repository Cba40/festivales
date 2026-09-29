import { useEffect, useId, useState } from 'react';
import { AlertTriangle, Pencil } from 'lucide-react';
import { useAppStore } from '@/core/state/store';
import type { OperationalObservationDTO } from '../types';
import { Button } from './ui';

const SOURCES = [
  { value: 'manual', label: 'Manual' },
  { value: 'sensor', label: 'Sensor' },
  { value: 'official_report', label: 'Reporte oficial' },
];

const FIELD_CLASSES =
  'mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500';

/**
 * Nombre que el backend va a registrar en `corrected_by`: el `sub` del JWT.
 * Se decodifica del token solo para mostrarlo. Si no se puede decodificar se
 * muestra un placeholder, pero el nombre igual queda bien: lo pone el servidor,
 * no este componente.
 */
function currentUserName(): string {
  const token = useAppStore.getState().auth.token;
  if (!token) return 'tu usuario';
  try {
    const payload = JSON.parse(
      atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))
    ) as { sub?: string };
    return payload.sub || 'tu usuario';
  } catch {
    return 'tu usuario';
  }
}

function notasDe(obs: OperationalObservationDTO): string {
  const notas = obs.metadata?.notas;
  return typeof notas === 'string' ? notas : '';
}

export interface ObservationEditModalProps {
  observation: OperationalObservationDTO | null;
  isSaving: boolean;
  onSave: (
    obs: OperationalObservationDTO,
    payload: { observed_density: number; observer_id?: string; source: string; metadata?: Record<string, unknown> }
  ) => void;
  onClose: () => void;
}

/**
 * Corrección in-place de una observación (RFC-006).
 *
 * El modal NO ofrece timestamp, zona ni jornada: el backend los rechaza con 422
 * (`extra="forbid"`), así que offeringlos sería una acción que nunca puede
 * funcionar. Tampoco ofrece "corregido por": ese campo lo escribe el servidor
 * con el `sub` del token y se muestra en solo lectura para que el operador sepa
 * a nombre de quién va a quedar registrada la corrección.
 */
export function ObservationEditModal({
  observation,
  isSaving,
  onSave,
  onClose,
}: ObservationEditModalProps) {
  const [density, setDensity] = useState('');
  const [observerId, setObserverId] = useState('');
  const [source, setSource] = useState('manual');
  const [notas, setNotas] = useState('');
  const [error, setError] = useState<string | null>(null);
  const titleId = useId();
  const densityInputId = useId();

  const obs = observation;
  // `Number('')` es 0, así que un campo vacío se leería como "cambió a 0" y
  // mostraría el aviso de recálculo sin motivo.
  const densityChanged = obs ? density.trim() !== '' && Number(density) !== obs.observed_density : false;

  // El modal se reutiliza para filas distintas: se rehidrata cuando cambia la
  // observación abierta, no solo en el primer mount.
  useEffect(() => {
    if (!obs) return;
    setDensity(String(obs.observed_density));
    setObserverId(obs.observer_id ?? '');
    setSource(obs.source);
    setNotas(notasDe(obs));
    setError(null);
  }, [obs]);

  useEffect(() => {
    if (!obs) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isSaving) onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [obs, isSaving, onClose]);

  if (!obs) return null;

  const handleSubmit = () => {
    const parsed = Number(density);
    if (density.trim() === '' || !Number.isFinite(parsed)) {
      setError('La densidad observada debe ser un número.');
      return;
    }
    if (!Number.isInteger(parsed) || parsed < 0) {
      setError('La densidad observada debe ser un entero mayor o igual a 0.');
      return;
    }
    setError(null);
    onSave(obs, {
      observed_density: parsed,
      ...(observerId.trim() !== '' ? { observer_id: observerId.trim() } : {}),
      source,
      ...(notas.trim() !== '' ? { metadata: { notas: notas.trim() } } : {}),
    });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto"
      >
        <h2 id={titleId} className="text-lg font-semibold text-slate-800 mb-1 flex items-center gap-2">
          <Pencil className="w-4 h-4" />
          Corregir observación
        </h2>
        <p className="text-xs text-slate-500 mb-4">
          La corrección queda registrada a nombre de{' '}
          <span className="font-medium text-slate-700">{currentUserName()}</span>. La zona,
          la jornada y la fecha/hora no se pueden modificar.
        </p>

        <div className="space-y-4">
          <div>
            <label htmlFor={densityInputId} className="block text-sm">
              <span className="text-slate-700 font-medium">Densidad observada</span>
              <input
                id={densityInputId}
                type="number"
                min={0}
                step={1}
                value={density}
                onChange={(e) => setDensity(e.target.value)}
                className={FIELD_CLASSES}
                disabled={isSaving}
              />
            </label>
            {densityChanged && (
              <p className="mt-1 flex items-start gap-1 text-xs text-amber-700">
                <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                Las alertas de esta observación se van a recalcular con el valor nuevo.
              </p>
            )}
          </div>

          <label className="block text-sm">
            <span className="text-slate-700 font-medium">Observador (opcional)</span>
            <input
              type="text"
              value={observerId}
              onChange={(e) => setObserverId(e.target.value)}
              placeholder="UUID del observador"
              className={FIELD_CLASSES}
              disabled={isSaving}
            />
          </label>

          <label className="block text-sm">
            <span className="text-slate-700 font-medium">Fuente</span>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className={FIELD_CLASSES}
              disabled={isSaving}
            >
              {SOURCES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm">
            <span className="text-slate-700 font-medium">Notas (opcional)</span>
            <input
              type="text"
              value={notas}
              onChange={(e) => setNotas(e.target.value)}
              placeholder="Motivo de la corrección"
              className={FIELD_CLASSES}
              disabled={isSaving}
            />
          </label>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={onClose} disabled={isSaving}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={isSaving}>
            {isSaving ? 'Guardando...' : 'Guardar corrección'}
          </Button>
        </div>
      </div>
    </div>
  );
}
