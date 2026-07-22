import { useState, useCallback, useEffect } from 'react';
import { useRecommendationConfig, useStage4Config, useMotorConfigMutations } from '../hooks/useMotorConfig';

function SliderField({
  label, value, onChange, min, max, step, disabled,
}: {
  label: string; value: number; onChange: (v: number) => void;
  min: number; max: number; step: number; disabled: boolean;
}) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-slate-700 font-medium">{label}</span>
        <span className="text-slate-500 font-mono tabular-nums">{value.toFixed(2)}</span>
      </div>
      <input
        type="range"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        min={min} max={max} step={step}
        disabled={disabled}
        className="w-full accent-blue-600 disabled:opacity-50"
      />
      <div className="flex justify-between text-xs text-slate-400">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}

function WaitTimeRow({
  row, index, onChange, onRemove, disabled,
}: {
  row: number[]; index: number;
  onChange: (i: number, field: number, value: number) => void;
  onRemove: (i: number) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-slate-500 w-6">{index + 1}.</span>
      <input
        type="number"
        value={row[0]}
        onChange={(e) => onChange(index, 0, parseFloat(e.target.value) || 0)}
        disabled={disabled}
        className="w-20 px-2 py-1 border border-slate-300 rounded text-sm"
        placeholder="Desde"
        step={0.05}
      />
      <span className="text-slate-400">→</span>
      <input
        type="number"
        value={row[1]}
        onChange={(e) => onChange(index, 1, parseFloat(e.target.value) || 0)}
        disabled={disabled}
        className="w-20 px-2 py-1 border border-slate-300 rounded text-sm"
        placeholder="Hasta"
        step={0.05}
      />
      <span className="text-slate-400">=</span>
      <input
        type="number"
        value={row[2]}
        onChange={(e) => onChange(index, 2, parseInt(e.target.value) || 0)}
        disabled={disabled}
        className="w-20 px-2 py-1 border border-slate-300 rounded text-sm"
        placeholder="Min"
        step={1}
      />
      <span className="text-slate-500 text-xs">min</span>
      {!disabled && (
        <button
          onClick={() => onRemove(index)}
          className="text-red-500 hover:text-red-700 text-lg leading-none ml-1"
          title="Eliminar fila"
        >
          ×
        </button>
      )}
    </div>
  );
}

function ConfigSection({
  title, icon, children,
}: {
  title: string; icon: string; children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
        <span className="text-lg">{icon}</span>
        <h2 className="font-bold text-slate-800">{title}</h2>
      </div>
      <div className="p-5 space-y-4">
        {children}
      </div>
    </div>
  );
}

export function MotorConfigScreen() {
  const { config: recConfig, loading: loadingRec, refresh: refreshRec } = useRecommendationConfig();
  const { config: stgConfig, loading: loadingStg, refresh: refreshStg } = useStage4Config();
  const { updateRecommendation, updateStage4, saving, error } = useMotorConfigMutations();

  const [draftRec, setDraftRec] = useState<Record<string, number> | null>(null);
  const [draftStg, setDraftStg] = useState<Record<string, number | number[][]> | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (recConfig && !draftRec) {
      const { created_at, updated_at, ...fields } = recConfig;
      setDraftRec(fields as Record<string, number>);
    }
  }, [recConfig, draftRec]);

  useEffect(() => {
    if (stgConfig && !draftStg) {
      const { created_at, updated_at, ...fields } = stgConfig;
      setDraftStg(fields as unknown as Record<string, number | number[][]>);
    }
  }, [stgConfig, draftStg]);

  const handleRecChange = useCallback((field: string, value: number) => {
    setDraftRec((prev) => prev ? { ...prev, [field]: value } : prev);
  }, []);

  const handleStgChange = useCallback((field: string, value: number | number[][]) => {
    setDraftStg((prev) => prev ? { ...prev, [field]: value } : prev);
  }, []);

  const handleWaitRowChange = useCallback((index: number, field: number, value: number) => {
    setDraftStg((prev) => {
      if (!prev) return prev;
      const mapping = (prev.wait_time_mapping as number[][]) || [];
      const updated = mapping.map((row, i) =>
        i === index ? row.map((v, j) => j === field ? value : v) : row
      );
      return { ...prev, wait_time_mapping: updated };
    });
  }, []);

  const handleAddWaitRow = useCallback(() => {
    setDraftStg((prev) => {
      if (!prev) return prev;
      const mapping = (prev.wait_time_mapping as number[][]) || [];
      const last = mapping.length > 0 ? mapping[mapping.length - 1][1] : 0;
      return { ...prev, wait_time_mapping: [...mapping, [last, last + 0.2, 0]] };
    });
  }, []);

  const handleRemoveWaitRow = useCallback((index: number) => {
    setDraftStg((prev) => {
      if (!prev) return prev;
      const mapping = (prev.wait_time_mapping as number[][]) || [];
      return { ...prev, wait_time_mapping: mapping.filter((_, i) => i !== index) };
    });
  }, []);

  const handleSaveRec = useCallback(async () => {
    if (!draftRec) return;
    setSuccessMsg(null);
    const result = await updateRecommendation(draftRec);
    if (result) {
      setSuccessMsg('Configuración de recomendaciones guardada');
      setDraftRec(null);
      refreshRec();
    }
  }, [draftRec, updateRecommendation, refreshRec]);

  const handleSaveStg = useCallback(async () => {
    if (!draftStg) return;
    setSuccessMsg(null);
    const result = await updateStage4(draftStg as Record<string, unknown>);
    if (result) {
      setSuccessMsg('Configuración Stage 4 guardada');
      setDraftStg(null);
      refreshStg();
    }
  }, [draftStg, updateStage4, refreshStg]);

  const loading = loadingRec || loadingStg;

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold text-slate-800">Configuración del Motor</h1>
        <button
          onClick={() => { setDraftRec(null); setDraftStg(null); refreshRec(); refreshStg(); }}
          disabled={loading}
          className="text-sm px-3 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-600 font-medium"
        >
          {loading ? 'Cargando...' : 'Recargar'}
        </button>
      </header>

      <main className="p-6 max-w-3xl mx-auto space-y-6">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
        )}
        {successMsg && (
          <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">{successMsg}</div>
        )}

        {/* Recommendation Config */}
        <ConfigSection title="Recomendaciones" icon="⚙️">
          {!draftRec ? (
            <p className="text-sm text-slate-400">Cargando...</p>
          ) : (
            <div className="space-y-5">
              <SliderField label="Umbral de saturación baja" value={draftRec.low_density_saturation_threshold} onChange={(v) => handleRecChange('low_density_saturation_threshold', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Umbral de razonamiento baja densidad" value={draftRec.low_density_reasoning_threshold} onChange={(v) => handleRecChange('low_density_reasoning_threshold', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Penalización por zona regulada" value={draftRec.regulated_penalty} onChange={(v) => handleRecChange('regulated_penalty', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Bonus VIP" value={draftRec.vip_bonus} onChange={(v) => handleRecChange('vip_bonus', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Bonus Staff" value={draftRec.staff_bonus} onChange={(v) => handleRecChange('staff_bonus', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Penalización por movilidad" value={draftRec.mobility_penalty} onChange={(v) => handleRecChange('mobility_penalty', v)} min={0} max={1} step={0.05} disabled={saving} />
              <div className="pt-2">
                <button
                  onClick={handleSaveRec}
                  disabled={saving}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg text-sm disabled:opacity-50"
                >
                  {saving ? 'Guardando...' : 'Guardar Configuración'}
                </button>
              </div>
            </div>
          )}
        </ConfigSection>

        {/* Stage 4 Config */}
        <ConfigSection title="Stage 4 — Derivation de Estado" icon="🧩">
          {!draftStg ? (
            <p className="text-sm text-slate-400">Cargando...</p>
          ) : (
            <div className="space-y-5">
              <SliderField label="Umbral de saturación alta" value={draftStg.saturation_high_threshold as number} onChange={(v) => handleStgChange('saturation_high_threshold', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Umbral de saturación moderada" value={draftStg.saturation_moderate_threshold as number} onChange={(v) => handleStgChange('saturation_moderate_threshold', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Confianza (sin eventos)" value={draftStg.confidence_no_events as number} onChange={(v) => handleStgChange('confidence_no_events', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Confianza (eventos planificados)" value={draftStg.confidence_planned_events as number} onChange={(v) => handleStgChange('confidence_planned_events', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Confianza (incidente activo)" value={draftStg.confidence_incident as number} onChange={(v) => handleStgChange('confidence_incident', v)} min={0} max={1} step={0.05} disabled={saving} />

              <div className="pt-2 border-t border-slate-200">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-slate-700">Mapeo de tiempo de espera</h3>
                  {!saving && (
                    <button
                      onClick={handleAddWaitRow}
                      className="text-xs px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-600"
                    >
                      + Agregar rango
                    </button>
                  )}
                </div>
                <div className="space-y-1.5">
                  {(draftStg.wait_time_mapping as number[][] || []).map((row, i) => (
                    <WaitTimeRow
                      key={i}
                      row={row}
                      index={i}
                      onChange={handleWaitRowChange}
                      onRemove={handleRemoveWaitRow}
                      disabled={saving}
                    />
                  ))}
                </div>
              </div>

              <div className="pt-2">
                <button
                  onClick={handleSaveStg}
                  disabled={saving}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg text-sm disabled:opacity-50"
                >
                  {saving ? 'Guardando...' : 'Guardar Configuración'}
                </button>
              </div>
            </div>
          )}
        </ConfigSection>
      </main>
    </div>
  );
}
