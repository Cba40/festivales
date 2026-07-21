import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDashboardSync } from '../hooks/useDashboardSync';
import { ZoneStatusCard } from '../components/ZoneStatusCard';
import { useAppStore } from '../../../core/state/store';

export function DashboardScreen() {
  const { zones, incidents, refresh, loading } = useDashboardSync();
  const navigate = useNavigate();
  const logout = useAppStore((state) => state.logout);

  const handleLogout = () => { logout(); navigate('/'); };

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold text-slate-800">Operación Territorial</h1>
        <div className="flex gap-4">
          <button
            onClick={() => navigate('/dashboard/event-days')}
            className="text-sm bg-indigo-600 hover:bg-indigo-700 text-white py-1 px-3 rounded font-medium"
          >
            Días
          </button>
          <button
            onClick={() => navigate('/dashboard/profiles')}
            className="text-sm bg-amber-600 hover:bg-amber-700 text-white py-1 px-3 rounded font-medium"
          >
            Perfiles
          </button>
          <button
            onClick={() => navigate('/dashboard/phases')}
            className="text-sm bg-cyan-600 hover:bg-cyan-700 text-white py-1 px-3 rounded font-medium"
          >
            Fases
          </button>
          <button
            onClick={() => navigate('/dashboard/context-engine')}
            className="text-sm bg-purple-600 hover:bg-purple-700 text-white py-1 px-3 rounded font-medium"
          >
            Motor
          </button>
          <button
            onClick={() => navigate('/dashboard/admin-zones')}
            className="text-sm bg-emerald-600 hover:bg-emerald-700 text-white py-1 px-3 rounded font-medium"
          >
            Admin. Zonas
          </button>
          <button 
            onClick={() => navigate('/dashboard/zones')}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            Ver Zonas
          </button>
          <button 
            onClick={() => refresh()}
            disabled={loading}
            className="text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 py-1 px-3 rounded"
          >
            {loading ? 'Actualizando...' : 'Actualizar'}
          </button>
          <button onClick={handleLogout} type="button" className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors">Cerrar Sesión</button>
        </div>
      </header>

      <main className="p-6 max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
        <section>
          <h2 className="text-lg font-semibold text-slate-700 mb-4">Estado de Zonas</h2>
          <div className="space-y-4 max-h-[calc(100vh-150px)] overflow-y-auto pr-2">
            {zones.map((zone) => (
              <ZoneStatusCard key={zone.id} zone={zone} />
            ))}
          </div>
        </section>

        <section>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-slate-700">Incidentes Activos</h2>
            <button
              onClick={() => navigate('/dashboard/report')}
              className="bg-red-600 hover:bg-red-700 text-white py-1 px-4 rounded text-sm font-medium"
            >
              Reportar
            </button>
          </div>
          <div className="space-y-4">
            {incidents.filter(i => i.status !== 'resuelto').map((incident) => (
              <div key={incident.id} className="bg-white p-4 rounded-lg shadow-sm border border-l-4 border-l-red-500">
                <div className="flex justify-between mb-2">
                  <span className="text-xs font-bold uppercase text-red-600">{incident.type}</span>
                  <span className="text-xs text-slate-500">{new Date(incident.createdAt).toLocaleTimeString()}</span>
                </div>
                <p className="text-sm text-slate-700">{incident.description}</p>
                <div className="mt-2 text-xs text-slate-500 font-medium">
                  Severidad: {incident.severity}
                </div>
              </div>
            ))}
            {incidents.length === 0 && (
              <p className="text-sm text-slate-500 italic">No hay incidentes activos.</p>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
