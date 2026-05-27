// src/features/dashboard/screens/IncidentReportScreen.tsx

import { useNavigate } from 'react-router-dom';
import { ArrowLeft, AlertTriangle } from 'lucide-react';
import { IncidentForm } from '../components/IncidentForm';

export default function IncidentReportScreen() {
  const navigate = useNavigate();

  const handleSuccess = () => {
    // Redirigir al dashboard tras confirmación
    setTimeout(() => {
      navigate('/dashboard');
    }, 300);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-blue-50/30">
      {/* Header */}
      <header className="sticky top-0 z-30 backdrop-blur-xl bg-white/80 border-b border-slate-200/60 px-4 sm:px-6 lg:px-8 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-4">
          <button
            onClick={() => navigate('/dashboard')}
            className="w-9 h-9 rounded-xl bg-slate-100 hover:bg-slate-200 flex items-center justify-center transition-colors cursor-pointer"
          >
            <ArrowLeft size={18} className="text-slate-600" />
          </button>
          <div>
            <h1 className="text-lg font-black text-slate-900 tracking-tight flex items-center gap-2">
              <AlertTriangle size={20} className="text-orange-500" />
              Reportar Incidente
            </h1>
            <p className="text-[11px] text-slate-500">
              Completá los datos para registrar un nuevo incidente operativo
            </p>
          </div>
        </div>
      </header>

      {/* Form container */}
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-3xl border border-slate-200/60 shadow-sm p-6 sm:p-8">
          <IncidentForm onSuccess={handleSuccess} />
        </div>

        {/* Info footer */}
        <p className="text-center text-[11px] text-slate-400 mt-6">
          Los incidentes reportados son visibles para todo el equipo operativo.
          <br />
          Se notificará al coordinador de zona correspondiente.
        </p>
      </main>
    </div>
  );
}
