import { useState } from 'react';
import { EventDayScreen } from './EventDayScreen';
import { AttendanceLevelScreen } from './AttendanceLevelScreen';
import { DashboardHeader } from '../components/DashboardHeader';

type Section = 'days' | 'attendance';

const SECTIONS: { key: Section; label: string }[] = [
  { key: 'days', label: 'Días del Evento' },
  { key: 'attendance', label: 'Niveles de Asistencia' },
];

export function EventConfigScreen() {
  const [activeSection, setActiveSection] = useState<Section>('days');

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <DashboardHeader title="Jornadas y Fases" />
      <div className="flex flex-wrap gap-2 px-4 sm:px-6 py-3">
        {SECTIONS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveSection(key)}
            className={`text-sm font-medium px-4 py-2 rounded-lg transition-colors ${
              activeSection === key
                ? 'bg-indigo-600 text-white'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <main className="p-4 sm:p-6">
        {activeSection === 'days' && <EventDayScreen />}
        {activeSection === 'attendance' && <AttendanceLevelScreen />}
      </main>
    </div>
  );
}