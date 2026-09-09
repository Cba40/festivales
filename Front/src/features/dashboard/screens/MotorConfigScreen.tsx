import { useState, useCallback, useEffect } from 'react';
import { useRecommendationConfig, useStage4Config, useMotorConfigMutations } from '../hooks/useMotorConfig';

function SliderField({
  label, hint, value, onChange, min, max, step, disabled,
}: {
  label: string; hint?: string; value: number; onChange: (v: number) => void;
  min: number; max: number; step: number; disabled: boolean;
}) {
  return (
    <div className="space-y-1" title={hint}>
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
        title={hint}
        aria-label={hint ? `${label}: ${hint}` : label}
        className="w-full accent-blue-600 disabled:opacity-50"
      />
      <div className="flex justify-between text-xs text-slate-400">
        <span>{min}</span>
        <span>{max}</span>
      </div>
      {hint && (
        <p className="text-xs text-slate-400 leading-snug">{hint}</p>
      )}
    </div>
  );
}

const CONFIG_SAVED_MSG = '✅ Configuración aplicada correctamente. Se reflejará en la próxima predicción.';

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
  const [draftStg, setDraftStg] = useState<Record<string, number> | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (recConfig && !draftRec) {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { created_at, updated_at, ...fields } = recConfig;
      setDraftRec(fields as Record<string, number>);
    }
  }, [recConfig, draftRec]);

  useEffect(() => {
    if (stgConfig && !draftStg) {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { created_at, updated_at, ...fields } = stgConfig;
      setDraftStg(fields as Record<string, number>);
    }
  }, [stgConfig, draftStg]);

  const handleRecChange = useCallback((field: string, value: number) => {
    setDraftRec((prev) => prev ? { ...prev, [field]: value } : prev);
  }, []);

  const handleStgChange = useCallback((field: string, value: number) => {
    setDraftStg((prev) => prev ? { ...prev, [field]: value } : prev);
  }, []);

  const handleSaveRec = useCallback(async () => {
    if (!draftRec) return;
    setSuccessMsg(null);
    const result = await updateRecommendation(draftRec);
    if (result) {
      setSuccessMsg(CONFIG_SAVED_MSG);
      setDraftRec(null);
      refreshRec();
    }
  }, [draftRec, updateRecommendation, refreshRec]);

  const handleSaveStg = useCallback(async () => {
    if (!draftStg) return;
    setSuccessMsg(null);
    const result = await updateStage4(draftStg);
    if (result) {
      setSuccessMsg(CONFIG_SAVED_MSG);
      setDraftStg(null);
      refreshStg();
    }
  }, [draftStg, updateStage4, refreshStg]);

  const loading = loadingRec || loadingStg;

  return (
    <main className="max-w-3xl mx-auto space-y-6">
      <div className="flex justify-end">
        <button
          onClick={() => { setDraftRec(null); setDraftStg(null); refreshRec(); refreshStg(); }}
          disabled={loading}
          className="text-sm px-3 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-600 font-medium"
        >
          {loading ? 'Cargando...' : 'Recargar'}
        </button>
      </div>
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
              <SliderField label="Umbral de saturación baja" hint="Filtra zonas cuya saturación supere este nivel al buscar baja densidad." value={draftRec.low_density_saturation_threshold} onChange={(v) => handleRecChange('low_density_saturation_threshold', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Umbral de razonamiento baja densidad" hint="Muestra 'Baja densidad proyectada' si la saturación es menor a este umbral." value={draftRec.low_density_reasoning_threshold} onChange={(v) => handleRecChange('low_density_reasoning_threshold', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Penalización por zona regulada" hint="Penaliza el score de zonas con restricción REGULATED." value={draftRec.regulated_penalty} onChange={(v) => handleRecChange('regulated_penalty', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Bonus VIP" hint="Suma al score de los usuarios con acceso VIP." value={draftRec.vip_bonus} onChange={(v) => handleRecChange('vip_bonus', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Bonus Staff" hint="Suma al score de los usuarios con acceso STAFF." value={draftRec.staff_bonus} onChange={(v) => handleRecChange('staff_bonus', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Penalización por movilidad" hint="Penaliza el score cuando la zona no es la actual del usuario." value={draftRec.mobility_penalty} onChange={(v) => handleRecChange('mobility_penalty', v)} min={0} max={1} step={0.05} disabled={saving} />
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
              <SliderField label="Umbral de saturación alta" hint="Con densidad/capacidad ≥ este valor la zona se clasifica como alta demanda." value={draftStg.saturation_high_threshold} onChange={(v) => handleStgChange('saturation_high_threshold', v)} min={0} max={1} step={0.05} disabled={saving} />
              <SliderField label="Umbral de saturación moderada" hint="Con densidad/capacidad ≥ este valor la zona se clasifica como demanda moderada." value={draftStg.saturation_moderate_threshold} onChange={(v) => handleStgChange('saturation_moderate_threshold', v)} min={0} max={1} step={0.05} disabled={saving} />

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
  );
}
