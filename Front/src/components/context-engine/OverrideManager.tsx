import { useState, useEffect, useCallback } from 'react';
import { Plus, XCircle, Clock, AlertTriangle } from 'lucide-react';
import { EVENT_ID } from './constants';
import { useOverrides, useEventStates, useZoneTypes } from '../../hooks/useContextEngine';
import type { StateOverrideDTO, StateOverrideCreatePayload } from '../../hooks/useContextEngine';

interface OverrideManagerProps {
  eventDayId: string;
  eventId?: string;
}

export function OverrideManager({ eventDayId, eventId }: OverrideManagerProps) {
  const eid = eventId || EVENT_ID;
  const { states: eventStates, loading: statesLoading } = useEventStates(eid);
  const { types: zoneTypes, loading: typesLoading } = useZoneTypes();
  const { overrides, saving, error, createOverride, cancelOverride } = useOverrides(eid);

  const [showForm, setShowForm] = useState(false);
  const [stateId, setStateId] = useState('');
  const [startDate, setStartDate] = useState(() => new Date().toISOString().slice(0, 16));
  const [endDate, setEndDate] = useState(() => {
    const d = new Date();
    d.setHours(d.getHours() + 4);
    return d.toISOString().slice(0, 16);
  });
  const [reason, setReason] = useState('');
  const [zoneTypeId, setZoneTypeId] = useState('');
  const [formErrors, setFormErrors] = useState<string[]>([]);

  useEffect(() => {
    if (eventStates.length > 0 && !stateId) {
      const fallback = eventStates.find(s => s.slug === 'temprano') ?? eventStates[0];
      setStateId(fallback.id);
    }
  }, [eventStates, stateId]);

  const activeOverrides = overrides.filter(o => o.is_active);

  const validateForm = useCallback(() => {
    const errs: string[] = [];
    if (!stateId) errs.push('Seleccioná un estado');
    if (!startDate) errs.push('Seleccioná fecha/hora de inicio');
    if (!endDate) errs.push('Seleccioná fecha/hora de fin');
    if (startDate && endDate && startDate >= endDate) errs.push('La fecha de fin debe ser posterior al inicio');
    if (!reason.trim()) errs.push('El motivo no puede estar vacío');
    return errs;
  }, [stateId, startDate, endDate, reason]);

  const handleSubmit = useCallback(async () => {
    const errs = validateForm();
    setFormErrors(errs);
    if (errs.length > 0) return;

    const payload: StateOverrideCreatePayload = {
      event_day_id: eventDayId,
      event_state_id: stateId,
      zone_type_id: zoneTypeId || null,
      start_time: new Date(startDate).toISOString(),
      end_time: new Date(endDate).toISOString(),
      reason: reason.trim(),
      created_by: 'operator',
    };

    const result = await createOverride(payload);
    if (result) {
      setShowForm(false);
      setReason('');
      setZoneTypeId('');
    }
  }, [validateForm, stateId, startDate, endDate, reason, zoneTypeId, eventDayId, createOverride]);

  const handleCancel = useCallback(async (override: StateOverrideDTO) => {
    await cancelOverride(override.id);
  }, [cancelOverride]);

  const loading = statesLoading || typesLoading;

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
      )}

      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">Overrides activos</h3>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-1 text-xs bg-indigo-600 hover:bg-indigo-700 text-white py-1.5 px-3 rounded-lg font-medium transition-colors"
          >
            <Plus className="w-3.5 h-3.5" /> Nuevo override
          </button>
        )}
      </div>

      {loading && (
        <div className="text-center py-6 text-slate-400 italic text-sm">Cargando catálogos...</div>
      )}

      {showForm && !loading && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
          <h4 className="text-sm font-semibold text-slate-700">Crear override</h4>

          {formErrors.length > 0 && (
            <div className="space-y-1">
              {formErrors.map((err, i) => (
                <div key={i} className="flex items-start gap-1.5 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
                  <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                  <span>{err}</span>
                </div>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Estado a forzar</label>
              <select
                value={stateId}
                onChange={(e) => setStateId(e.target.value)}
                className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {eventStates.map(st => (
                  <option key={st.id} value={st.id}>{st.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Aplica a tipo de zona</label>
              <select
                value={zoneTypeId}
                onChange={(e) => setZoneTypeId(e.target.value)}
                className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Todas las zonas</option>
                {zoneTypes.map(zt => (
                  <option key={zt.id} value={zt.id}>{zt.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Inicio</label>
              <input
                type="datetime-local"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Fin</label>
              <input
                type="datetime-local"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Motivo</label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Ej: Corte de calle programado"
              className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <button
              onClick={() => { setShowForm(false); setFormErrors([]); }}
              disabled={saving}
              className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50"
            >
              Cancelar
            </button>
            <button
              onClick={handleSubmit}
              disabled={saving}
              className="px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
            >
              {saving ? 'Creando...' : 'Crear override'}
            </button>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {activeOverrides.length === 0 && !showForm && (
          <div className="text-center py-6 text-slate-400 italic text-sm">No hay overrides activos</div>
        )}
        {activeOverrides.map(ov => {
          const st = eventStates.find(s => s.id === ov.event_state_id);
          const zt = zoneTypes.find(t => t.id === ov.zone_type_id);
          return (
            <div
              key={ov.id}
              className="flex items-start gap-3 p-3 bg-white border border-slate-200 rounded-lg shadow-sm"
            >
              <div
                className="w-3 h-3 rounded-full mt-1 shrink-0"
                style={{ backgroundColor: st?.color ?? '#94a3b8' }}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-slate-800">{st?.name ?? 'Desconocido'}</span>
                  {ov.zone_type_id && (
                    <span className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">
                      {zt?.name ?? 'Específico'}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-0.5">{ov.reason}</p>
                <div className="flex items-center gap-3 mt-1 text-[10px] text-slate-400">
                  <span className="flex items-center gap-1"><Clock className="w-2.5 h-2.5" />{new Date(ov.start_time).toLocaleString()}</span>
                  <span>→</span>
                  <span>{new Date(ov.end_time).toLocaleString()}</span>
                </div>
              </div>
              <button
                onClick={() => handleCancel(ov)}
                className="shrink-0 text-red-400 hover:text-red-600 transition-colors"
                title="Cancelar override"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
