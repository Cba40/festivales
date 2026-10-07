import { BATHROOM_USE_RATE_HELP } from '../../utils/bathroomUseRate';

interface Props {
  value: string;
  onChange: (value: string) => void;
  error?: string | null;
}

/**
 * Input de `bathroom_use_rate_per_person_hour` (usos/persona-hora).
 * Solo se monta cuando el subtipo es `banos`. Los modales que lo exponen
 * escriben la misma fila de `service_configs`, por lo que quedan sincronizados
 * entre sí.
 */
export function BathroomUseRateField({ value, onChange, error }: Props) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        Tasa de uso (usos/persona-hora) *
      </label>
      <input
        type="number"
        min={0}
        step="0.01"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        title="Hipótesis inicial: 0.1. Calibrar con observaciones reales"
        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
      />
      <p className="text-[10px] text-slate-400 mt-0.5">{BATHROOM_USE_RATE_HELP}</p>
      {error && (
        <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-md p-2 mt-2">
          {error}
        </p>
      )}
    </div>
  );
}