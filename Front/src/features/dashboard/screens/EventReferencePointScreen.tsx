import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEventReferencePoint } from '../hooks/useEventReferencePoint';
import { EventReferencePointMap } from '../components/EventReferencePointMap';

export function EventReferencePointScreen() {
  const navigate = useNavigate();
  const { event, loading, saving, saved, error, load, save } = useEventReferencePoint();

  const [lat, setLat] = useState('');
  const [lng, setLng] = useState('');
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (event && !touched) {
      setLat(event.reference_point_latitude != null ? String(event.reference_point_latitude) : '');
      setLng(event.reference_point_longitude != null ? String(event.reference_point_longitude) : '');
    }
  }, [event, touched]);

  const parsedLat = lat.trim() === '' ? null : Number(lat);
  const parsedLng = lng.trim() === '' ? null : Number(lng);
  const canSave = parsedLat != null && parsedLng != null && Number.isFinite(parsedLat) && Number.isFinite(parsedLng);

  const handleSave = async () => {
    if (!canSave) return;
    const ok = await save({
      reference_point_latitude: parsedLat,
      reference_point_longitude: parsedLng,
    });
    setTouched(false);
    if (ok) {
      setLat(String(parsedLat));
      setLng(String(parsedLng));
    }
  };

  const savedLat = event?.reference_point_latitude ?? null;
  const savedLng = event?.reference_point_longitude ?? null;

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

          <p className="text-xs text-slate-500">
            Ingresá los valores manualmente. No se edita desde el mapa.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Latitud</span>
              <input
                type="number"
                step="any"
                min={-90}
                max={90}
                value={lat}
                disabled={loading}
                onChange={(e) => { setTouched(true); setLat(e.target.value); }}
                placeholder="-30.975000"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Longitud</span>
              <input
                type="number"
                step="any"
                min={-180}
                max={180}
                value={lng}
                disabled={loading}
                onChange={(e) => { setTouched(true); setLng(e.target.value); }}
                placeholder="-64.090000"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </label>
          </div>

          <button
            onClick={handleSave}
            disabled={!canSave || saving || loading}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white py-2 px-6 rounded text-sm font-medium"
          >
            {saving ? 'Guardando...' : 'Guardar'}
          </button>
        </section>

        <section className="bg-white rounded-lg shadow-sm border border-slate-200 p-6 space-y-4">
          <h3 className="text-base font-semibold text-slate-700">Visualización en el mapa</h3>
          <EventReferencePointMap lat={savedLat} lng={savedLng} />
        </section>
      </main>
    </div>
  );
}