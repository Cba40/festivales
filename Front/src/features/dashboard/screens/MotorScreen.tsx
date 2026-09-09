import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { MotorConfigScreen } from './MotorConfigScreen';
import { EventConfigPage } from '../../../pages/EventConfigPage';
import { ObservationsScreen } from './ObservationsScreen';
import { AnalyticsScreen } from './AnalyticsScreen';

type Section = 'config' | 'predictions' | 'observations' | 'analytics';

const SECTIONS: { key: Section; label: string }[] = [
  { key: 'config', label: 'Configuración' },
  { key: 'predictions', label: 'Predicciones' },
  { key: 'observations', label: 'Observaciones' },
  { key: 'analytics', label: 'Analytics' },
];

const SECTION_KEYS: Section[] = SECTIONS.map((s) => s.key);

export function MotorScreen() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedTab = searchParams.get('tab') as Section | null;
  const [activeSection, setActiveSection] = useState<Section>(
    requestedTab && SECTION_KEYS.includes(requestedTab) ? requestedTab : 'config',
  );

  const selectSection = (section: Section) => {
    setActiveSection(section);
    setSearchParams({ tab: section });
  };

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <h1 className="text-xl font-bold text-slate-800">Motor</h1>
        <div className="flex gap-2 mt-3">
          {SECTIONS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => selectSection(key)}
              className={`text-sm font-medium px-4 py-2 rounded-lg transition-colors ${
                activeSection === key
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </header>

      <main className="p-6">
        {activeSection === 'config' && <MotorConfigScreen />}
        {activeSection === 'predictions' && <EventConfigPage />}
        {activeSection === 'observations' && <ObservationsScreen />}
        {activeSection === 'analytics' && <AnalyticsScreen />}
      </main>
    </div>
  );
}