import { useState, useCallback, useMemo, useEffect } from 'react';
import { useOperationalPhases } from '../hooks/useOperationalPhases';
import { useOperationalProfiles } from '../hooks/useOperationalProfiles';
import { useZoneBehaviors, useZoneTypes } from '../hooks/useZoneBehaviors';
import { useZoneBehaviorMutations } from '../hooks/useZoneBehaviorMutations';
import type { ZoneBehaviorDTO } from '../types';

function FlowRestrictionSelect({ value, onChange, disabled }: { value: string; onChange: (v: 'OPEN' | 'REGULATED' | 'CLOSED') => void; disabled: boolean }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as 'OPEN' | 'REGULATED' | 'CLOSED')}
      disabled={disabled}
      className="px-2 py-1 border border-slate-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
    >
      <option value="OPEN">Abierto</option>
      <option value="REGULATED">Regulado</option>
      <option value="CLOSED">Cerrado</option>
    </select>
  );
}

interface LocalRow {
  zoneTypeId: string;
  zoneTypeName: string;
  behavior: ZoneBehaviorDTO | null;
  densityFactor: number;
  flowRestriction: 'OPEN' | 'REGULATED' | 'CLOSED';
  dirty: boolean;
}

export function ZoneBehaviorScreen() {
  const { profiles } = useOperationalProfiles();
  const [selectedProfileId, setSelectedProfileId] = useState<string>('');
  const { phases, loading: loadingPhases } = useOperationalPhases(selectedProfileId);
  const [selectedPhaseId, setSelectedPhaseId] = useState<string>('');
  const { behaviors, loading: loadingBehaviors, error } = useZoneBehaviors(selectedPhaseId);
  const { zoneTypes, loading: loadingZoneTypes } = useZoneTypes();
  const { update, saving } = useZoneBehaviorMutations();

  const [rows, setRows] = useState<LocalRow[]>([]);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);

  const behaviorByZoneType = useMemo(() => {
    const map = new Map<string, ZoneBehaviorDTO>();
    for (const b of behaviors) {
      map.set(b.zone_type_id, b);
    }
    return map;
  }, [behaviors]);

  useEffect(() => {
    if (!zoneTypes.length) return;
    const map = behaviorByZoneType;
    const next = zoneTypes.map((zt) => {
      const existing = map.get(zt.id);
      return {
        zoneTypeId: zt.id,
        zoneTypeName: zt.name,
        behavior: existing ?? null,
        densityFactor: existing?.density_factor ?? 0.5,
        flowRestriction: existing?.flow_restriction ?? 'OPEN' as const,
        dirty: false,
      };
    });
    setRows(next);
  }, [zoneTypes, behaviorByZoneType]);

  const handleDensityChange = useCallback((zoneTypeId: string, value: number) => {
    setRows((prev) => prev.map((r) =>
      r.zoneTypeId === zoneTypeId ? { ...r, densityFactor: value, dirty: true } : r
    ));
  }, []);

  const handleFlowRestrictionChange = useCallback((zoneTypeId: string, value: 'OPEN' | 'REGULATED' | 'CLOSED') => {
    setRows((prev) => prev.map((r) =>
      r.zoneTypeId === zoneTypeId ? { ...r, flowRestriction: value, dirty: true } : r
    ));
  }, []);

  const handleSave = useCallback(async (row: LocalRow) => {
    if (!row.behavior) return;
    setSaveError(null);
    setSavingId(row.behavior.id);
    const result = await update(row.behavior.id, {
      density_factor: row.densityFactor,
      flow_restriction: row.flowRestriction,
    });
    setSavingId(null);
    if (result) {
      setRows((prev) => prev.map((r) =>
        r.zoneTypeId === row.zoneTypeId ? { ...r, dirty: false } : r
      ));
    } else {
      setSaveError('Error al guardar. Revisá los datos e intentá de nuevo.');
    }
  }, [update]);

  const handleProfileChange = useCallback((profileId: string) => {
    setSelectedProfileId(profileId);
    setSelectedPhaseId('');
  }, []);

  const hasUnsaved = rows.some((r) => r.dirty);

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold text-slate-800">Comportamiento Territorial</h1>
      </header>

      <main className="p-6 max-w-5xl mx-auto">
        {saveError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {saveError}
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Perfil operativo</label>
            <select
              value={selectedProfileId}
              onChange={(e) => handleProfileChange(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Seleccionar perfil...</option>
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Fase operativa</label>
            <select
              value={selectedPhaseId}
              onChange={(e) => setSelectedPhaseId(e.target.value)}
              disabled={!selectedProfileId || loadingPhases}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              <option value="">Seleccionar fase...</option>
              {phases.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
        </div>

        {loadingBehaviors || loadingZoneTypes ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 text-center text-slate-500">
            Cargando...
          </div>
        ) : !selectedPhaseId ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 text-center text-slate-500">
            Seleccioná un perfil y una fase para configurar los comportamientos territoriales.
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            {hasUnsaved && (
              <div className="px-4 py-2 bg-amber-50 border-b border-amber-200 text-sm text-amber-700">
                Tenés cambios sin guardar. Usá el botón Guardar en cada fila modificada.
              </div>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-slate-500">
                    <th className="px-4 py-3 font-medium">Tipo de Zona</th>
                    <th className="px-4 py-3 font-medium">Density Factor</th>
                    <th className="px-4 py-3 font-medium">Flow Restriction</th>
                    <th className="px-4 py-3 font-medium text-right">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const isLoading = saving && savingId === row.behavior?.id;
                    return (
                      <tr key={row.zoneTypeId} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="px-4 py-3 text-slate-800 font-medium">{row.zoneTypeName}</td>
                        <td className="px-4 py-3">
                          <input
                            type="number"
                            min={0}
                            max={1}
                            step={0.05}
                            value={row.densityFactor}
                            onChange={(e) => handleDensityChange(row.zoneTypeId, parseFloat(e.target.value) || 0)}
                            className="w-24 px-2 py-1 border border-slate-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <FlowRestrictionSelect
                            value={row.flowRestriction}
                            onChange={(v) => handleFlowRestrictionChange(row.zoneTypeId, v)}
                            disabled={!row.behavior}
                          />
                        </td>
                        <td className="px-4 py-3 text-right">
                          {row.behavior ? (
                            <button
                              onClick={() => handleSave(row)}
                              disabled={!row.dirty || isLoading}
                              className={`text-xs font-medium px-3 py-1.5 rounded transition-colors ${
                                row.dirty && !isLoading
                                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                                  : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                              }`}
                            >
                              {isLoading ? 'Guardando...' : 'Guardar'}
                            </button>
                          ) : (
                            <span className="text-xs text-slate-400">Sin registro</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
