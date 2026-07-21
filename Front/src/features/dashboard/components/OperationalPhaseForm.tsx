import { useState, useEffect } from 'react';
import type { OperationalProfileDTO } from '../types';

interface OperationalPhaseFormProps {
  profiles: OperationalProfileDTO[];
  selectedProfileId: string;
  initial?: {
    operational_profile_id: string;
    name: string;
    start_min: number;
    end_min: number;
    sort_order: number;
  } | null;
  onSave: (payload: {
    operational_profile_id: string;
    name: string;
    start_min: number;
    end_min: number;
    sort_order: number;
  }) => Promise<void>;
  onCancel: () => void;
  saving: boolean;
}

function timeStrToMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number);
  return h * 60 + m;
}

function minutesToTimeStr(min: number): string {
  const h = Math.floor(min / 60).toString().padStart(2, '0');
  const m = (min % 60).toString().padStart(2, '0');
  return `${h}:${m}`;
}

export function OperationalPhaseForm({
  profiles,
  selectedProfileId,
  initial,
  onSave,
  onCancel,
  saving,
}: OperationalPhaseFormProps) {
  const [profileId, setProfileId] = useState(selectedProfileId);
  const [name, setName] = useState('');
  const [startStr, setStartStr] = useState('');
  const [endStr, setEndStr] = useState('');
  const [sortOrder, setSortOrder] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (initial) {
      setProfileId(initial.operational_profile_id);
      setName(initial.name);
      setStartStr(minutesToTimeStr(initial.start_min));
      setEndStr(minutesToTimeStr(initial.end_min));
      setSortOrder(initial.sort_order.toString());
    } else {
      setProfileId(selectedProfileId);
      setName('');
      setStartStr('');
      setEndStr('');
      setSortOrder('');
    }
  }, [initial, selectedProfileId]);

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
    if (!profileId) {
      setValidationError('Debe seleccionar un perfil operativo');
      return;
    }
    if (!startStr || !endStr) {
      setValidationError('Los minutos de inicio y fin son obligatorios');
      return;
    }

    const startMin = timeStrToMinutes(startStr);
    const endMin = timeStrToMinutes(endStr);

    if (endMin <= startMin) {
      setValidationError('El minuto de fin debe ser mayor al minuto de inicio');
      return;
    }

    const parsedSortOrder = sortOrder !== '' ? parseInt(sortOrder, 10) : 0;
    if (isNaN(parsedSortOrder) || parsedSortOrder < 0) {
      setValidationError('El orden debe ser un número mayor o igual a 0');
      return;
    }

    await onSave({
      operational_profile_id: profileId,
      name: trimmedName,
      start_min: startMin,
      end_min: endMin,
      sort_order: parsedSortOrder,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Perfil operativo *</label>
        <select
          value={profileId}
          onChange={(e) => setProfileId(e.target.value)}
          required
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Seleccionar perfil...</option>
          {profiles.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Inicio (minuto del día) *</label>
          <input
            type="time"
            value={startStr}
            onChange={(e) => setStartStr(e.target.value)}
            required
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-[10px] text-slate-400 mt-0.5">Ej: 08:00 = 480 min</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Fin (minuto del día) *</label>
          <input
            type="time"
            value={endStr}
            onChange={(e) => setEndStr(e.target.value)}
            required
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-[10px] text-slate-400 mt-0.5">Ej: 12:00 = 720 min</p>
        </div>
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
          disabled={saving || !name.trim() || !profileId || !startStr || !endStr}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {saving ? 'Guardando...' : initial ? 'Actualizar' : 'Crear fase'}
        </button>
      </div>
    </form>
  );
}
