import { useState, useCallback } from 'react';
import { OperationalProfileList } from '../components/OperationalProfileList';
import { OperationalProfileForm } from '../components/OperationalProfileForm';
import { OperationalPhaseList } from '../components/OperationalPhaseList';
import { OperationalPhaseForm } from '../components/OperationalPhaseForm';
import { useOperationalProfiles } from '../hooks/useOperationalProfiles';
import { useOperationalProfileMutations } from '../hooks/useOperationalProfileMutations';
import { useOperationalPhases } from '../hooks/useOperationalPhases';
import { useOperationalPhaseMutations } from '../hooks/useOperationalPhaseMutations';
import type { OperationalProfileDTO, OperationalPhaseDTO } from '../types';
import { apiClient } from '@/core/api/client';

export function OperationalProfileScreen() {
  const { profiles, loading, error, refresh } = useOperationalProfiles();
  const { create, update, remove, saving } = useOperationalProfileMutations();

  const [showForm, setShowForm] = useState(false);
  const [editingProfile, setEditingProfile] = useState<OperationalProfileDTO | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const { phases, loading: phasesLoading, refresh: refreshPhases } = useOperationalPhases(
    editingProfile?.id ?? null
  );
  const {
    create: createPhase,
    update: updatePhase,
    remove: removePhase,
    saving: savingPhase,
  } = useOperationalPhaseMutations();

  const [showPhaseForm, setShowPhaseForm] = useState(false);
  const [editingPhase, setEditingPhase] = useState<OperationalPhaseDTO | null>(null);
  const [phaseError, setPhaseError] = useState<string | null>(null);

  const handleNew = () => {
    setEditingProfile(null);
    setFormError(null);
    setShowPhaseForm(false);
    setEditingPhase(null);
    setShowForm(true);
  };

  const handleEdit = useCallback(async (profile: OperationalProfileDTO) => {
    setFormError(null);
    setShowPhaseForm(false);
    setEditingPhase(null);
    try {
      const { data } = await apiClient.get<OperationalProfileDTO>(
        `/operational-profiles/${profile.id}`
      );
      setEditingProfile(data);
      setShowForm(true);
    } catch {
      setFormError('Error al cargar los datos del perfil');
    }
  }, []);

  const handleDelete = useCallback(
    async (id: string) => {
      if (!window.confirm('¿Eliminar este perfil operativo? Esta acción no se puede deshacer.')) return;
      const ok = await remove(id);
      if (ok) {
        refresh();
        if (editingProfile?.id === id) {
          setEditingProfile(null);
          setShowForm(false);
        }
      }
    },
    [remove, refresh, editingProfile]
  );

  const handleSave = useCallback(
    async (payload: { name: string; description?: string | null }) => {
      setFormError(null);
      let result: OperationalProfileDTO | null;
      if (editingProfile) {
        result = await update(editingProfile.id, payload);
      } else {
        result = await create(payload);
      }
      if (result) {
        setEditingProfile(result);
        setShowForm(true);
        refresh();
      } else {
        setFormError('Error al guardar. Revisá los datos e intentá de nuevo.');
      }
    },
    [editingProfile, create, update, refresh]
  );

  const handleCancel = () => {
    setShowForm(false);
    setEditingProfile(null);
    setFormError(null);
    setShowPhaseForm(false);
    setEditingPhase(null);
  };

  const handleNewPhase = () => {
    setEditingPhase(null);
    setPhaseError(null);
    setShowPhaseForm(true);
  };

  const handleEditPhase = useCallback((phase: OperationalPhaseDTO) => {
    setPhaseError(null);
    setEditingPhase(phase);
    setShowPhaseForm(true);
  }, []);

  const handleDeletePhase = useCallback(
    async (id: string) => {
      if (!window.confirm('¿Eliminar esta fase? Esta acción no se puede deshacer.')) return;
      const ok = await removePhase(id);
      if (ok) refreshPhases();
    },
    [removePhase, refreshPhases]
  );

  const handleSavePhase = useCallback(
    async (payload: {
      operational_profile_id: string;
      name: string;
      sort_order: number;
    }) => {
      setPhaseError(null);
      let result: OperationalPhaseDTO | null;
      if (editingPhase) {
        result = await updatePhase(editingPhase.id, payload);
      } else {
        result = await createPhase(payload);
      }
      if (result) {
        setShowPhaseForm(false);
        setEditingPhase(null);
        refreshPhases();
      } else {
        setPhaseError('Error al guardar la fase. Revisá los datos e intentá de nuevo.');
      }
    },
    [editingPhase, createPhase, updatePhase, refreshPhases]
  );

  const handleCancelPhase = () => {
    setShowPhaseForm(false);
    setEditingPhase(null);
    setPhaseError(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold text-slate-800">Gestión de Perfiles Operativos</h1>
        {!showForm && (
          <button
            onClick={handleNew}
            className="bg-blue-600 hover:bg-blue-700 text-white py-1.5 px-4 rounded-lg text-sm font-medium transition-colors"
          >
            + Nuevo perfil
          </button>
        )}
      </header>

      <main className="p-6 max-w-3xl mx-auto">
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

        {showForm ? (
          <>
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
              <h2 className="text-lg font-semibold text-slate-800 mb-4">
                {editingProfile ? 'Editar perfil' : 'Nuevo perfil operativo'}
              </h2>
              <OperationalProfileForm
                initial={editingProfile ? { name: editingProfile.name, description: editingProfile.description } : null}
                onSave={handleSave}
                onCancel={handleCancel}
                saving={saving}
              />
            </div>

            {editingProfile && (
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-semibold text-slate-800">Fases del perfil</h2>
                  {!showPhaseForm && (
                    <button
                      onClick={handleNewPhase}
                      className="bg-blue-600 hover:bg-blue-700 text-white py-1.5 px-4 rounded-lg text-sm font-medium transition-colors"
                    >
                      + Nueva fase
                    </button>
                  )}
                </div>

                {phaseError && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                    {phaseError}
                  </div>
                )}

                {showPhaseForm ? (
                  <div className="mb-6 p-4 border border-slate-200 rounded-lg">
                    <h3 className="text-md font-semibold text-slate-800 mb-3">
                      {editingPhase ? 'Editar fase' : 'Nueva fase'}
                    </h3>
                    <OperationalPhaseForm
                      operationalProfileId={editingProfile.id}
                      initial={editingPhase ? { name: editingPhase.name, sort_order: editingPhase.sort_order } : null}
                      onSave={handleSavePhase}
                      onCancel={handleCancelPhase}
                      saving={savingPhase}
                    />
                  </div>
                ) : null}

                {phasesLoading ? (
                  <div className="text-center py-4 text-slate-500">Cargando fases...</div>
                ) : (
                  <OperationalPhaseList
                    phases={phases}
                    onEdit={handleEditPhase}
                    onDelete={handleDeletePhase}
                  />
                )}
              </div>
            )}
          </>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Perfiles cargados</h2>
            {loading ? (
              <div className="text-center py-8 text-slate-500">Cargando...</div>
            ) : (
              <OperationalProfileList
                profiles={profiles}
                onEdit={handleEdit}
                onDelete={handleDelete}
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}
