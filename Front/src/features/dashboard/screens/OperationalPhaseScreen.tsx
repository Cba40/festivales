import { useState, useCallback } from 'react';
import { OperationalPhaseList } from '../components/OperationalPhaseList';
import { OperationalPhaseForm } from '../components/OperationalPhaseForm';
import { useOperationalPhases } from '../hooks/useOperationalPhases';
import { useOperationalPhaseMutations } from '../hooks/useOperationalPhaseMutations';
import { useOperationalProfiles } from '../hooks/useOperationalProfiles';
import type { OperationalPhaseDTO } from '../types';
import { apiClient } from '@/core/api/client';

export function OperationalPhaseScreen() {
  const { profiles } = useOperationalProfiles();
  const [selectedProfileId, setSelectedProfileId] = useState<string>('');
  const { phases, loading, error, refresh } = useOperationalPhases(selectedProfileId);
  const { create, update, remove, saving } = useOperationalPhaseMutations();

  const [showForm, setShowForm] = useState(false);
  const [editingPhase, setEditingPhase] = useState<OperationalPhaseDTO | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const handleNew = () => {
    if (!selectedProfileId) return;
    setEditingPhase(null);
    setFormError(null);
    setShowForm(true);
  };

  const handleEdit = useCallback(async (phase: OperationalPhaseDTO) => {
    setFormError(null);
    try {
      const { data } = await apiClient.get<OperationalPhaseDTO>(
        `/operational-phases/${phase.id}`
      );
      setEditingPhase(data);
      setShowForm(true);
    } catch {
      setFormError('Error al cargar los datos de la fase');
    }
  }, []);

  const handleDelete = useCallback(
    async (id: string) => {
      if (!window.confirm('¿Eliminar esta fase operativa? Esta acción no se puede deshacer.')) return;
      const ok = await remove(id);
      if (ok) refresh();
    },
    [remove, refresh]
  );

  const handleSave = useCallback(
    async (payload: {
      operational_profile_id: string;
      name: string;
      start_min: number;
      end_min: number;
      sort_order: number;
    }) => {
      setFormError(null);
      let result: OperationalPhaseDTO | null;
      if (editingPhase) {
        result = await update(editingPhase.id, payload);
      } else {
        result = await create(payload);
      }
      if (result) {
        setShowForm(false);
        setEditingPhase(null);
        refresh();
      } else {
        setFormError('Error al guardar. Revisá los datos e intentá de nuevo.');
      }
    },
    [editingPhase, create, update, refresh]
  );

  const handleCancel = () => {
    setShowForm(false);
    setEditingPhase(null);
    setFormError(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold text-slate-800">Gestión de Fases Operativas</h1>
        {!showForm && selectedProfileId && (
          <button
            onClick={handleNew}
            className="bg-blue-600 hover:bg-blue-700 text-white py-1.5 px-4 rounded-lg text-sm font-medium transition-colors"
          >
            + Nueva fase
          </button>
        )}
      </header>

      <main className="p-6 max-w-4xl mx-auto">
        {formError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {formError}
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
            {error}
          </div>
        )}

        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 mb-1">Perfil operativo</label>
          <select
            value={selectedProfileId}
            onChange={(e) => { setSelectedProfileId(e.target.value); setShowForm(false); setEditingPhase(null); }}
            className="w-full max-w-md px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Seleccionar perfil para ver sus fases...</option>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        {showForm ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">
              {editingPhase ? 'Editar fase' : 'Nueva fase operativa'}
            </h2>
            <OperationalPhaseForm
              profiles={profiles}
              selectedProfileId={selectedProfileId}
              initial={editingPhase ? {
                operational_profile_id: editingPhase.operational_profile_id,
                name: editingPhase.name,
                start_min: editingPhase.start_min,
                end_min: editingPhase.end_min,
                sort_order: editingPhase.sort_order,
              } : null}
              onSave={handleSave}
              onCancel={handleCancel}
              saving={saving}
            />
          </div>
        ) : selectedProfileId ? (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Fases del perfil</h2>
            {loading ? (
              <div className="text-center py-8 text-slate-500">Cargando...</div>
            ) : (
              <OperationalPhaseList
                phases={phases}
                profiles={profiles}
                onEdit={handleEdit}
                onDelete={handleDelete}
              />
            )}
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 text-center py-8 text-slate-500">
            Seleccioná un perfil operativo para administrar sus fases.
          </div>
        )}
      </main>
    </div>
  );
}
