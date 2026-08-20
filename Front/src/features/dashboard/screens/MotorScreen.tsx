import { useState } from 'react';
import { MotorConfigScreen } from './MotorConfigScreen';
import { EventConfigPage } from '../../../pages/EventConfigPage';

type Section = 'config' | 'predictions';

const SECTIONS: { key: Section; label: string }[] = [
  { key: 'config', label: 'Configuración' },
  { key: 'predictions', label: 'Predicciones' },
];

export function MotorScreen() {
  const [activeSection, setActiveSection] = useState<Section>('config');

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <h1 className="text-xl font-bold text-slate-800">Motor</h1>
        <div className="flex gap-2 mt-3">
          {SECTIONS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveSection(key)}
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
      </main>
    </div>
  );
}