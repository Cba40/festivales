import { useNavigate } from 'react-router-dom';
import { ZoneManagementPanel } from '../components/ZoneManagementPanel';

export function ZoneAdminScreen() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => navigate('/dashboard')}
          className="text-slate-500 hover:text-slate-800"
        >
          &larr; Volver
        </button>
        <h1 className="text-xl font-bold text-slate-800">Administración de Zonas</h1>
      </header>

      <main className="p-6 max-w-4xl mx-auto">
        <ZoneManagementPanel />
      </main>
    </div>
  );
}
