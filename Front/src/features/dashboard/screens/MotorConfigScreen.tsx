import { useState, useCallback, useEffect } from 'react';
import { HelpCircle, ChevronDown, ChevronUp, CheckCircle2, Info, Settings, Puzzle, RefreshCw } from 'lucide-react';
import { useRecommendationConfig, useStage4Config, useMotorConfigMutations } from '../hooks/useMotorConfig';
import { Button, Card } from '../components/ui';

function HelpTip({ text }: { text: string }) {
  return (
    <span className="relative inline-flex items-center">
      <HelpCircle className="w-4 h-4 text-slate-400 hover:text-slate-600 cursor-help" aria-label="Ayuda" />
      <span className="pointer-events-none absolute left-0 top-full mt-2 z-20 hidden group-hover:block w-72 rounded-lg bg-slate-900 text-slate-100 text-xs leading-relaxed p-3 shadow-lg">
        {text}
      </span>
    </span>
  );
}

function SliderField({
  label, hint, value, onChange, min, max, step, disabled,
}: {
  label: string; hint?: string; value: number; onChange: (v: number) => void;
  min: number; max: number; step: number; disabled: boolean;
}) {
  return (
    <div className="group space-y-1">
      <div className="flex justify-between text-sm items-center gap-2">
        <span className="text-slate-700 font-medium flex items-center gap-1.5">
          {label}
          {hint && <HelpTip text={hint} />}
        </span>
        <span className="text-slate-500 font-mono tabular-nums">{value.toFixed(2)}</span>
      </div>
      <input
        type="range"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        min={min} max={max} step={step}
        disabled={disabled}
        aria-label={hint ? `${label}: ${hint}` : label}
        className="w-full accent-indigo-600 disabled:opacity-50"
      />
      <div className="flex justify-between text-xs text-slate-400">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}

const CONFIG_SAVED_MSG = 'Configuración aplicada correctamente. Se reflejará en la próxima predicción.';

function ConfigSection({
  title, icon, children,
}: {
  title: string; icon: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <Card variant="standard">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-indigo-500">{icon}</span>
        <h2 className="font-bold text-slate-800">{title}</h2>
      </div>
      <div className="space-y-4">
        {children}
      </div>
    </Card>
  );
}

const HELP_CONTENT = [
  'La Configuración de Recomendaciones ajusta cómo el motor puntúa y filtra las zonas para los usuarios.',
  'La Configuración Stage 4 define cómo se clasifica el estado operativo (saturación) de cada zona en tiempo real.',
  'Los cambios se guardan en la base de datos y se aplican inmediatamente en la siguiente predicción de todos los operadores.',
];

export function MotorConfigScreen() {
  const { config: recConfig, loading: loadingRec, refresh: refreshRec } = useRecommendationConfig();
  const { config: stgConfig, loading: loadingStg, refresh: refreshStg } = useStage4Config();
  const { updateRecommendation, updateStage4, saving, error } = useMotorConfigMutations();

  const [draftRec, setDraftRec] = useState<Record<string, number> | null>(null);
  const [draftStg, setDraftStg] = useState<Record<string, number> | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState(false);

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

  useEffect(() => {
    if (!successMsg) return;
    const timer = setTimeout(() => setSuccessMsg(null), 4000);
    return () => clearTimeout(timer);
  }, [successMsg]);

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

  const handleDiscardRec = useCallback(() => {
    if (!recConfig) return;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { created_at, updated_at, ...fields } = recConfig;
    setDraftRec(fields as Record<string, number>);
  }, [recConfig]);

  const handleDiscardStg = useCallback(() => {
    if (!stgConfig) return;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { created_at, updated_at, ...fields } = stgConfig;
    setDraftStg(fields as Record<string, number>);
  }, [stgConfig]);

  const hasRecChanges = useCallback(() => {
    if (!draftRec || !recConfig) return false;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { created_at, updated_at, ...config } = recConfig;
    return Object.entries(config as Record<string, number>)
      .some(([key, value]) => draftRec[key] !== value);
  }, [draftRec, recConfig]);

  const hasStgChanges = useCallback(() => {
    if (!draftStg || !stgConfig) return false;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { created_at, updated_at, ...config } = stgConfig;
    return Object.entries(config as Record<string, number>)
      .some(([key, value]) => draftStg[key] !== value);
  }, [draftStg, stgConfig]);

  const recDirty = hasRecChanges();
  const stgDirty = hasStgChanges();
  const loading = loadingRec || loadingStg;

  return (
    <main className="max-w-3xl mx-auto space-y-6">
      {/* Ayuda general colapsable */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <button
          onClick={() => setShowHelp((prev) => !prev)}
          className="w-full px-5 py-3 flex items-center justify-between text-left bg-slate-50 hover:bg-slate-100 transition-colors"
        >
          <span className="font-bold text-slate-800 flex items-center gap-2">
            <Info className="w-4 h-4 text-indigo-500" />
            ¿Cómo funciona esta configuración?
          </span>
          {showHelp ? (
            <ChevronUp className="w-5 h-5 text-slate-500" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-500" />
          )}
        </button>
        {showHelp && (
          <div className="px-5 py-4 space-y-2">
            {HELP_CONTENT.map((line) => (
              <p key={line} className="text-sm text-slate-600 leading-relaxed">
                {parseBold(line)}
              </p>
            ))}
          </div>
        )}
      </div>

      <div className="flex justify-end">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => { setDraftRec(null); setDraftStg(null); refreshRec(); refreshStg(); }}
          disabled={loading}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          {loading ? 'Cargando...' : 'Recargar'}
        </Button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
      )}
      {successMsg && (
        <div role="status" className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-700 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          {successMsg}
        </div>
      )}

      {/* Recommendation Config */}
      <ConfigSection title="Recomendaciones" icon={<Settings className="w-5 h-5" />}>
        {!draftRec ? (
          <p className="text-sm text-slate-400">Cargando...</p>
        ) : (
          <div className="space-y-5">
            <SliderField label="Umbral de saturación baja" hint="Zonas con saturación por encima de este valor se filtran cuando el usuario busca 'baja densidad'." value={draftRec.low_density_saturation_threshold} onChange={(v) => handleRecChange('low_density_saturation_threshold', v)} min={0} max={1} step={0.05} disabled={saving} />
            <SliderField label="Umbral de razonamiento baja densidad" hint="Si la saturación es menor a este valor, se agrega la etiqueta 'Baja densidad proyectada' a la recomendación." value={draftRec.low_density_reasoning_threshold} onChange={(v) => handleRecChange('low_density_reasoning_threshold', v)} min={0} max={1} step={0.05} disabled={saving} />
            <SliderField label="Penalización por zona regulada" hint="Reduce la probabilidad de recomendar zonas con restricción 'REGULATED'." value={draftRec.regulated_penalty} onChange={(v) => handleRecChange('regulated_penalty', v)} min={0} max={1} step={0.05} disabled={saving} />
            <SliderField label="Bonus VIP" hint="Aumenta la prioridad de las recomendaciones para usuarios con este rol." value={draftRec.vip_bonus} onChange={(v) => handleRecChange('vip_bonus', v)} min={0} max={1} step={0.05} disabled={saving} />
            <SliderField label="Bonus Staff" hint="Aumenta la prioridad de las recomendaciones para usuarios con este rol." value={draftRec.staff_bonus} onChange={(v) => handleRecChange('staff_bonus', v)} min={0} max={1} step={0.05} disabled={saving} />
            <SliderField label="Penalización por movilidad" hint="Reduce el score si la zona recomendada está lejos de la ubicación actual del usuario." value={draftRec.mobility_penalty} onChange={(v) => handleRecChange('mobility_penalty', v)} min={0} max={1} step={0.05} disabled={saving} />
            <div className="pt-2 flex items-center gap-3 flex-wrap">
              <Button
                onClick={handleSaveRec}
                disabled={saving || !recDirty}
              >
                {saving ? 'Guardando...' : 'Guardar Configuración'}
              </Button>
              <Button
                variant="secondary"
                onClick={handleDiscardRec}
                disabled={saving || !recDirty}
              >
                Descartar cambios
              </Button>
            </div>
          </div>
        )}
      </ConfigSection>

      {/* Stage 4 Config */}
      <ConfigSection title="Stage 4 — Derivation de Estado" icon={<Puzzle className="w-5 h-5" />}>
        {!draftStg ? (
          <p className="text-sm text-slate-400">Cargando...</p>
        ) : (
          <div className="space-y-5">
            <SliderField label="Umbral de saturación alta" hint="Define el límite de densidad/capacidad para clasificar una zona como 'Alta Demanda'." value={draftStg.saturation_high_threshold} onChange={(v) => handleStgChange('saturation_high_threshold', v)} min={0} max={1} step={0.05} disabled={saving} />
            <SliderField label="Umbral de saturación moderada" hint="Define el límite de densidad/capacidad para clasificar una zona como 'Demanda Moderada'." value={draftStg.saturation_moderate_threshold} onChange={(v) => handleStgChange('saturation_moderate_threshold', v)} min={0} max={1} step={0.05} disabled={saving} />

            <div className="pt-2 flex items-center gap-3 flex-wrap">
              <Button
                onClick={handleSaveStg}
                disabled={saving || !stgDirty}
              >
                {saving ? 'Guardando...' : 'Guardar Configuración'}
              </Button>
              <Button
                variant="secondary"
                onClick={handleDiscardStg}
                disabled={saving || !stgDirty}
              >
                Descartar cambios
              </Button>
            </div>
          </div>
        )}
      </ConfigSection>
    </main>
  );
}

function parseBold(line: string): React.ReactNode {
  const parts = line.split('**');
  return parts.map((part, index) =>
    index % 2 === 1 ? <strong key={index} className="font-semibold text-slate-800">{part}</strong> : part
  );
}