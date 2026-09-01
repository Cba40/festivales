import { useNavigate } from 'react-router-dom';
import { ZoneStatusCard } from '../components/ZoneStatusCard';
import { useAppStore } from '../../../core/state/store';

export function DashboardScreen() {
  const zones = useAppStore((state) => state.zones);
  const navigate = useNavigate();
  const logout = useAppStore((state) => state.logout);

  const handleLogout = () => { logout(); navigate('/'); };

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold text-slate-800">Operación Territorial</h1>
        <div className="flex gap-4">
          <button
            onClick={() => navigate('/dashboard/event-config')}
            className="text-sm bg-indigo-600 hover:bg-indigo-700 text-white py-1 px-3 rounded font-medium"
          >
            Configuración del Evento
          </button>
          <button
            onClick={() => navigate('/dashboard/infrastructure')}
            className="text-sm bg-emerald-600 hover:bg-emerald-700 text-white py-1 px-3 rounded font-medium"
          >
            Infraestructura
          </button>
          <button
            onClick={() => navigate('/dashboard/operational-events')}
            className="text-sm bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded font-medium"
          >
            Eventos Imprevistos
          </button>
          <button
            onClick={() => navigate('/dashboard/motor')}
            className="text-sm bg-purple-600 hover:bg-purple-700 text-white py-1 px-3 rounded font-medium"
          >
            Motor
          </button>
          <button onClick={handleLogout} type="button" className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors">Cerrar Sesión</button>
        </div>
      </header>

      <main className="p-6 max-w-4xl mx-auto">
        <section>
          <h2 className="text-lg font-semibold text-slate-700 mb-4">Estado de Zonas</h2>
          <div className="space-y-4 max-h-[calc(100vh-150px)] overflow-y-auto pr-2">
            {zones.map((zone) => (
              <ZoneStatusCard key={zone.id} zone={zone} />
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
