import { useState } from 'react';
import { useZoneCreation } from '../hooks/useZoneCreation';
import { ZONE_TYPES } from '../constants';
import { AdminMapSelector } from '../../../components/AdminMapSelector';

const dynamicFields: Record<string, { name: string; key: string; type: string; placeholder: string }[]> = {
  estacionamiento: [
    { name: 'Disponibilidad (%)', key: 'disponibilidad', type: 'number', placeholder: '50' },
  ],
  transporte: [
    { name: 'Espera (min)', key: 'espera_min', type: 'number', placeholder: '10' },
    { name: 'Calle', key: 'calle', type: 'text', placeholder: 'Av. Principal' },
  ],
  comida: [
    { name: 'Espera (min)', key: 'espera_min', type: 'number', placeholder: '5' },
    { name: 'Subtipo', key: 'subtipo', type: 'text', placeholder: 'rapido / comida / bebida' },
  ],
  servicios: [
    { name: 'Subtipo', key: 'subtipo', type: 'text', placeholder: 'banos / hidratacion / descanso / salud' },
  ],
  emergencia: [
    { name: 'Dirección', key: 'direccion', type: 'text', placeholder: 'Av. Siempre Viva 123' },
    { name: 'Horario', key: 'horario', type: 'text', placeholder: '24hs' },
    { name: 'Teléfono', key: 'telefono', type: 'text', placeholder: '+543511234567' },
  ],
  descanso: [
    { name: 'Subtipo', key: 'subtipo', type: 'text', placeholder: 'descanso' },
    { name: 'X (0-100)', key: 'x', type: 'number', placeholder: '50' },
    { name: 'Y (0-100)', key: 'y', type: 'number', placeholder: '50' },
  ],
  salida: [
    { name: 'Transporte', key: 'transporte', type: 'text', placeholder: 'auto / transporte / peatonal' },
    { name: 'Espera (min)', key: 'espera_min', type: 'number', placeholder: '5' },
    { name: 'Capacidad estimada', key: 'capacidad_estimada', type: 'number', placeholder: '200' },
    { name: 'Es embudo', key: 'es_embudo', type: 'text', placeholder: 'true / false' },
  ],
};

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
  const [extra, setExtra] = useState<Record<string, string>>({});

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !capacity || Number(capacity) <= 0) return;

    const extraPayload: Record<string, string | number | boolean> = {};
    for (const [k, v] of Object.entries(extra)) {
      if (v === 'true') extraPayload[k] = true;
      else if (v === 'false') extraPayload[k] = false;
      else if (v && !isNaN(Number(v))) extraPayload[k] = Number(v);
      else extraPayload[k] = v;
    }

    await createZone({
      name: name.trim(),
      type,
      capacity: Number(capacity),
      lat: lat ? Number(lat) : undefined,
      lng: lng ? Number(lng) : undefined,
      ...extraPayload,
    });

    setName('');
    setType('estacionamiento');
    setCapacity('');
    setLat('');
    setLng('');
    setExtra({});
    if (onSuccess) onSuccess();
  };

  const fields = dynamicFields[type] || [];

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
          onChange={(e) => { setType(e.target.value); setExtra({}); }}
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

      <AdminMapSelector
        lat={lat ? Number(lat) : undefined}
        lng={lng ? Number(lng) : undefined}
        onChangeLocation={(newLat, newLng) => {
          setLat(String(newLat));
          setLng(String(newLng));
        }}
      />

      {fields.map((f) => (
        <div key={f.key}>
          <label className="block text-sm font-medium text-slate-700 mb-1">{f.name}</label>
          <input
            type={f.type}
            value={extra[f.key] || ''}
            onChange={(e) => setExtra(prev => ({ ...prev, [f.key]: e.target.value }))}
            placeholder={f.placeholder}
            className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      ))}

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
