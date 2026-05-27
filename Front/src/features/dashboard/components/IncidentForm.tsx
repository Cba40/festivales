import { useState } from 'react';
import { useIncidentMutations } from '../hooks/useIncidentMutations';
import { SeverityLevel } from '../types';

export function IncidentForm({ onSuccess }: { onSuccess?: () => void }) {
  const { reportIncident, loading } = useIncidentMutations();
  const [type, setType] = useState('congestion');
  const [severity, setSeverity] = useState<SeverityLevel>('media');
  const [description, setDescription] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;

    await reportIncident({
      type,
      severity,
      description,
      status: 'abierto',
    });

    setType('congestion');
    setSeverity('media');
    setDescription('');
    if (onSuccess) onSuccess();
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-sm border border-slate-200 space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Tipo de Incidente</label>
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="congestion">Congestión</option>
          <option value="closure">Cierre</option>
          <option value="emergency">Emergencia</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Severidad</label>
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value as SeverityLevel)}
          className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="baja">Baja</option>
          <option value="media">Media</option>
          <option value="alta">Alta</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Descripción</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
          rows={3}
          className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {loading ? 'Reportando...' : 'Reportar Incidente'}
      </button>
    </form>
  );
}
