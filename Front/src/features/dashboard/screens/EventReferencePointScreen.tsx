import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEventReferencePoint } from '../hooks/useEventReferencePoint';
import { AdminMapSelector } from '../../../components/AdminMapSelector';

export function EventReferencePointScreen() {
  const navigate = useNavigate();
  const { event, loading, saving, saved, error, load, save } = useEventReferencePoint();

  const [draftLat, setDraftLat] = useState<number | null>(null);
  const [draftLng, setDraftLng] = useState<number | null>(null);
  const [manual, setManual] = useState(false);
  const [mapKey, setMapKey] = useState(0);

  useEffect(() => {
    load();
  }, [load]);

  const savedLat = event?.reference_point_latitude ?? null;
  const savedLng = event?.reference_point_longitude ?? null;

  useEffect(() => {
    setDraftLat(savedLat);
    setDraftLng(savedLng);
    setManual(false);
  }, [savedLat, savedLng]);

  const effectiveLat = manual ? draftLat : savedLat;
  const effectiveLng = manual ? draftLng : savedLng;

  const dirty = manual && (draftLat !== savedLat || draftLng !== savedLng);
  const canSave = manual && draftLat != null && draftLng != null;

  const handleChangeLocation = (lat: number, lng: number) => {
    setDraftLat(lat);
    setDraftLng(lng);
    setManual(true);
  };

  const handleCancel = () => {
    setDraftLat(savedLat);
    setDraftLng(savedLng);
    setManual(false);
    setMapKey((k) => k + 1);
  };

  const handleSave = async () => {
    if (!canSave) return;
    const ok = await save({
      reference_point_latitude: draftLat,
      reference_point_longitude: draftLng,
    });
    if (ok) {
      setDraftLat(draftLat);
      setDraftLng(draftLng);
      setManual(false);
    }
  };

  const noReferencePoint = savedLat == null || savedLng == null;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-4">
        <button onClick={() => navigate('/dashboard')} className="text-slate-500 hover:text-slate-800">
          &larr; Volver
        </button>
        <h1 className="text-xl font-bold text-slate-800">Punto de Referencia Operacional</h1>
      </header>

      <main className="p-6 max-w-4xl mx-auto space-y-6">
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 text-sm rounded">
            {error}
          </div>
        )}
        {saved && !error && (
          <div className="bg-green-50 border-l-4 border-green-500 text-green-700 p-4 text-sm rounded">
            Punto de referencia operacional guardado correctamente.
          </div>
        )}

        <section className="bg-white rounded-lg shadow-sm border border-slate-200 p-6 space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-700">Punto de Referencia Operacional</h2>
            <p className="text-sm text-slate-500">
              Centro de gravedad operacional del evento. Es un dato fijo, independiente del día, perfil, fase o nivel de asistencia.
            </p>
          </div>

          {noReferencePoint && (
            <div className="bg-amber-50 border-l-4 border-amber-500 text-amber-700 p-4 text-sm rounded">
              El evento todavía no tiene un punto de referencia definido. Mové el marcador al punto deseado y guardalo.
            </div>
          )}

          {loading && !event ? (
            <div className="w-full bg-white rounded-lg border border-slate-200 h-[250px] flex items-center justify-center">
              <p className="text-sm text-slate-500 italic">Cargando evento...</p>
            </div>
          ) : (
            <AdminMapSelector
              key={mapKey}
              lat={effectiveLat ?? undefined}
              lng={effectiveLng ?? undefined}
              onChangeLocation={handleChangeLocation}
            />
          )}
        </section>

        <div className="flex gap-3">
          <button
            onClick={handleSave}
            disabled={!canSave || saving || loading}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white py-2 px-6 rounded text-sm font-medium"
          >
            {saving ? 'Guardando...' : 'Guardar'}
          </button>
          <button
            onClick={handleCancel}
            disabled={!dirty || saving || loading}
            className="bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 py-2 px-6 rounded text-sm font-medium"
          >
            Cancelar
          </button>
        </div>
      </main>
    </div>
  );
}