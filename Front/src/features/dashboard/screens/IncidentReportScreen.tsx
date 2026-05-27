import { useNavigate } from 'react-router-dom';
import { IncidentForm } from '../components/IncidentForm';

export function IncidentReportScreen() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center py-10">
      <div className="w-full max-w-lg">
        <button 
          onClick={() => navigate('/dashboard')}
          className="mb-6 text-slate-500 hover:text-slate-800 font-medium"
        >
          &larr; Volver al Dashboard
        </button>
        <h1 className="text-2xl font-bold text-slate-800 mb-6">Reportar Incidente</h1>
        <IncidentForm onSuccess={() => navigate('/dashboard')} />
      </div>
    </div>
  );
}
