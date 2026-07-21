import { useState, useEffect } from 'react';

interface AttendanceLevelFormProps {
  initial?: {
    name: string;
    min_people: number;
    max_people: number | null;
    global_multiplier: number;
  } | null;
  onSave: (payload: {
    name: string;
    min_people: number;
    max_people?: number | null;
    global_multiplier: number;
  }) => Promise<void>;
  onCancel: () => void;
  saving: boolean;
}

export function AttendanceLevelForm({ initial, onSave, onCancel, saving }: AttendanceLevelFormProps) {
  const [name, setName] = useState('');
  const [minPeople, setMinPeople] = useState('');
  const [maxPeople, setMaxPeople] = useState('');
  const [hasMax, setHasMax] = useState(true);
  const [globalMultiplier, setGlobalMultiplier] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (initial) {
      setName(initial.name);
      setMinPeople(initial.min_people.toString());
      if (initial.max_people !== null) {
        setHasMax(true);
        setMaxPeople(initial.max_people.toString());
      } else {
        setHasMax(false);
        setMaxPeople('');
      }
      setGlobalMultiplier(initial.global_multiplier.toString());
    } else {
      setName('');
      setMinPeople('');
      setMaxPeople('');
      setHasMax(true);
      setGlobalMultiplier('');
    }
  }, [initial]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    const trimmedName = name.trim();
    if (!trimmedName) {
      setValidationError('El nombre es obligatorio');
      return;
    }
    if (trimmedName.length > 50) {
      setValidationError('El nombre no puede superar los 50 caracteres');
      return;
    }

    const parsedMin = parseInt(minPeople, 10);
    if (isNaN(parsedMin) || parsedMin < 0) {
      setValidationError('El mínimo de personas debe ser un número mayor o igual a 0');
      return;
    }

    let parsedMax: number | null = null;
    if (hasMax) {
      parsedMax = parseInt(maxPeople, 10);
      if (isNaN(parsedMax) || parsedMax < 0) {
        setValidationError('El máximo de personas debe ser un número mayor o igual a 0');
        return;
      }
      if (parsedMax <= parsedMin) {
        setValidationError('El máximo debe ser mayor al mínimo');
        return;
      }
    }

    const parsedMultiplier = parseFloat(globalMultiplier);
    if (isNaN(parsedMultiplier)) {
      setValidationError('El multiplicador global debe ser un número válido');
      return;
    }
    if (parsedMultiplier < 0.1 || parsedMultiplier > 2.0) {
      setValidationError('El multiplicador debe estar entre 0.1 y 2.0');
      return;
    }

    await onSave({
      name: trimmedName,
      min_people: parsedMin,
      max_people: parsedMax,
      global_multiplier: parsedMultiplier,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={50}
          placeholder="Ej: 5.000 asistentes"
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Mínimo de personas *</label>
          <input
            type="number"
            min={0}
            value={minPeople}
            onChange={(e) => setMinPeople(e.target.value)}
            required
            placeholder="Ej: 0"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Máximo de personas
            <button
              type="button"
              onClick={() => { setHasMax(!hasMax); setMaxPeople(''); }}
              className="ml-2 text-xs text-blue-600 hover:text-blue-800"
            >
              {hasMax ? 'Sin límite' : 'Con límite'}
            </button>
          </label>
          {hasMax ? (
            <input
              type="number"
              min={0}
              value={maxPeople}
              onChange={(e) => setMaxPeople(e.target.value)}
              placeholder="Ej: 10000"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          ) : (
            <div className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm text-slate-400 bg-slate-50">
              Sin límite superior
            </div>
          )}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Multiplicador global *
          <span className="text-xs text-slate-400 ml-2">(0.1 – 2.0)</span>
        </label>
        <input
          type="number"
          min={0.1}
          max={2.0}
          step={0.01}
          value={globalMultiplier}
          onChange={(e) => setGlobalMultiplier(e.target.value)}
          required
          placeholder="Ej: 1.0"
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <p className="text-[10px] text-slate-400 mt-0.5">
          Factor que multiplica la capacidad de las zonas para proyectar densidad.
          El motor usa este valor en Stage 3.
        </p>
      </div>

      {validationError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {validationError}
        </div>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={saving || !name.trim() || !minPeople || !globalMultiplier}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {saving ? 'Guardando...' : initial ? 'Actualizar' : 'Crear nivel'}
        </button>
      </div>
    </form>
  );
}
