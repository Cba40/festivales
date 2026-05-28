import { useState } from 'react';
import { useZoneCreation } from '../hooks/useZoneCreation';

const ZONE_TYPES = [
  { value: 'estacionamiento', label: 'Estacionamiento' },
  { value: 'transporte', label: 'Transporte' },
  { value: 'comida', label: 'Comida' },
  { value: 'descanso', label: 'Descanso' },
  { value: 'servicios', label: 'Servicios' },
  { value: 'emergencia', label: 'Emergencia' },
];

interface Props {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function CreateZoneForm({ onSuccess, onCancel }: Props) {
  const { createZone, loading, error } = useZoneCreation();
  const [name, setName] = useState('');
  const [type, setType] = useState('estacionamiento');
  const [capacity, setCapacity] = useState('');
  const [lat, setLat] = useState('');
  const [lng, setLng] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !capacity || Number(capacity) <= 0) return;

    await createZone({
      name: name.trim(),
      type,
      capacity: Number(capacity),
      lat: lat ? Number(lat) : undefined,
      lng: lng ? Number(lng) : undefined,
    });

    setName('');
    setType('estacionamiento');
    setCapacity('');
    setLat('');
    setLng('');
    if (onSuccess) onSuccess();
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg border border-slate-200 space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Nombre de la Zona</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          placeholder="Ej: Estacionamiento Este"
          className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Tipo</label>
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
        >
          {ZONE_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Capacidad</label>
        <input
          type="number"
          value={capacity}
          onChange={(e) => setCapacity(e.target.value)}
          required
          min={1}
          placeholder="350"
          className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Latitud</label>
          <input
            type="number"
            step="any"
            value={lat}
            onChange={(e) => setLat(e.target.value)}
            placeholder="-30.9733"
            className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Longitud</label>
          <input
            type="number"
            step="any"
            value={lng}
            onChange={(e) => setLng(e.target.value)}
            placeholder="-64.0885"
            className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      </div>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
          {error}
        </div>
      )}

      <div className="flex justify-end gap-3 pt-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="py-2 px-4 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
          >
            Cancelar
          </button>
        )}
        <button
          type="submit"
          disabled={loading}
          className="py-2 px-4 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md transition-colors"
        >
          {loading ? 'Creando...' : 'Crear Zona'}
        </button>
      </div>
    </form>
  );
}
