import { useState, useEffect, useCallback } from 'react';
import { BarChart3, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { EVENT_ID } from '../components/context-engine/constants';
import { PredictionsDashboard } from '../components/context-engine/PredictionsDashboard';
import { apiClient } from '../core/api/client';

const TABS = [
  { id: 'predictions', label: 'Predicciones', icon: BarChart3 },
];

interface EventDaySummary {
  id: string;
  date: string;
  is_active: boolean;
}

export function EventConfigPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('predictions');
  const [eventDays, setEventDays] = useState<EventDaySummary[]>([]);
  const [selectedDayId, setSelectedDayId] = useState<string | null>(null);
  const [loadingDays, setLoadingDays] = useState(true);

  const loadDays = useCallback(async () => {
    setLoadingDays(true);
    try {
      const { data } = await apiClient.get<EventDaySummary[]>(`/events/${EVENT_ID}/event-days`);
      setEventDays(data);
      const today = data.find(d => d.is_active);
      if (today) {
        setSelectedDayId(today.id);
      } else if (data.length > 0) {
        setSelectedDayId(data[0].id);
      }
    } catch {
      /* ignore */
    } finally {
      setLoadingDays(false);
    }
  }, []);

  useEffect(() => {
    loadDays();
  }, [loadDays]);

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/dashboard')}
            className="text-slate-500 hover:text-slate-700 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-bold text-slate-800">Motor de Contexto</h1>
        </div>
        <select
          value={selectedDayId ?? ''}
          onChange={(e) => setSelectedDayId(e.target.value || null)}
          className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          disabled={loadingDays}
        >
          {loadingDays && <option value="">Cargando...</option>}
          {!loadingDays && eventDays.length === 0 && (
            <option value="">Sin jornadas</option>
          )}
          {eventDays.map(d => (
            <option key={d.id} value={d.id}>
              {d.date} {d.is_active ? '(Hoy)' : ''}
            </option>
          ))}
        </select>
      </header>

      <div className="border-b border-slate-200 bg-white">
        <div className="px-6 flex gap-1 overflow-x-auto">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <main className="p-6 max-w-7xl mx-auto">
        {!selectedDayId && !loadingDays && (
          <div className="text-center py-12 text-slate-400 italic">
            No hay jornadas disponibles.
          </div>
        )}

        {activeTab === 'predictions' && (
          <div className="bg-white border border-slate-200 rounded-xl p-6">
            <PredictionsDashboard eventId={EVENT_ID} />
          </div>
        )}
      </main>
    </div>
  );
}
