import { useState, useEffect } from 'react';

interface OperationalPhaseFormProps {
  operationalProfileId: string;
  initial?: {
    name: string;
    sort_order: number;
  } | null;
  onSave: (payload: {
    operational_profile_id: string;
    name: string;
    sort_order: number;
  }) => Promise<void>;
  onCancel: () => void;
  saving: boolean;
}

export function OperationalPhaseForm({
  operationalProfileId,
  initial,
  onSave,
  onCancel,
  saving,
}: OperationalPhaseFormProps) {
  const [name, setName] = useState('');
  const [sortOrder, setSortOrder] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (initial) {
      setName(initial.name);
      setSortOrder(initial.sort_order.toString());
    } else {
      setName('');
      setSortOrder('');
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
    if (trimmedName.length > 100) {
      setValidationError('El nombre no puede superar los 100 caracteres');
      return;
    }

    const parsedSortOrder = sortOrder !== '' ? parseInt(sortOrder, 10) : 0;
    if (isNaN(parsedSortOrder) || parsedSortOrder < 0) {
      setValidationError('El orden debe ser un número mayor o igual a 0');
      return;
    }

    await onSave({
      operational_profile_id: operationalProfileId,
      name: trimmedName,
      sort_order: parsedSortOrder,
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
          maxLength={100}
          placeholder="Ej: Apertura"
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Orden *</label>
        <input
          type="number"
          min={0}
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value)}
          required
          placeholder="Ej: 1"
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <p className="text-[10px] text-slate-400 mt-0.5">Define la secuencia de las fases dentro del perfil</p>
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
          disabled={saving || !name.trim()}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {saving ? 'Guardando...' : initial ? 'Actualizar' : 'Crear fase'}
        </button>
      </div>
    </form>
  );
}
