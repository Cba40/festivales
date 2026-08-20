import { useState } from 'react';
import { EventDayScreen } from './EventDayScreen';
import { AttendanceLevelScreen } from './AttendanceLevelScreen';
import { ServiceConfigScreen } from './ServiceConfigScreen';

type Section = 'days' | 'attendance' | 'services';

const SECTIONS: { key: Section; label: string }[] = [
  { key: 'days', label: 'Días del Evento' },
  { key: 'attendance', label: 'Niveles de Asistencia' },
  { key: 'services', label: 'Servicios' },
];

export function EventConfigScreen() {
  const [activeSection, setActiveSection] = useState<Section>('days');

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <h1 className="text-xl font-bold text-slate-800">Configuración del Evento</h1>
        <div className="flex gap-2 mt-3">
          {SECTIONS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveSection(key)}
              className={`text-sm font-medium px-4 py-2 rounded-lg transition-colors ${
                activeSection === key
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </header>

      <main className="p-6">
        {activeSection === 'days' && <EventDayScreen />}
        {activeSection === 'attendance' && <AttendanceLevelScreen />}
        {activeSection === 'services' && <ServiceConfigScreen />}
      </main>
    </div>
  );
}