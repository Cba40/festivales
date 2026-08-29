import { useState } from 'react';
import { ZoneAdminScreen } from './ZoneAdminScreen';
import { EventReferencePointScreen } from './EventReferencePointScreen';
import { ExitManagementScreen } from './ExitManagementScreen';
import { TransportManagementScreen } from './TransportManagementScreen';
import { AccommodationManagementScreen } from './AccommodationManagementScreen';
import { EmergencyManagementScreen } from './EmergencyManagementScreen';

const DEFAULT_EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

type Section = 'zones' | 'reference' | 'salidas' | 'transporte' | 'hospedaje' | 'emergencias';

const SECTIONS: { key: Section; label: string }[] = [
  { key: 'zones', label: 'Zonas' },
  { key: 'reference', label: 'Referencia Operativa' },
  { key: 'salidas', label: 'Salidas y Destinos' },
  { key: 'transporte', label: 'Transporte' },
  { key: 'hospedaje', label: 'Hospedaje' },
  { key: 'emergencias', label: 'Emergencias' },
];

export function InfrastructureScreen() {
  const [activeSection, setActiveSection] = useState<Section>('zones');

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <h1 className="text-xl font-bold text-slate-800">Infraestructura</h1>
        <div className="flex gap-2 mt-3">
          {SECTIONS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveSection(key)}
              className={`text-sm font-medium px-4 py-2 rounded-lg transition-colors ${
                activeSection === key
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </header>

      <main className="p-6">
        {activeSection === 'zones' && <ZoneAdminScreen />}
        {activeSection === 'reference' && <EventReferencePointScreen />}
        {activeSection === 'salidas' && <ExitManagementScreen eventId={DEFAULT_EVENT_ID} />}
        {activeSection === 'transporte' && (
          <TransportManagementScreen eventId={DEFAULT_EVENT_ID} />
        )}
        {activeSection === 'hospedaje' && (
          <AccommodationManagementScreen eventId={DEFAULT_EVENT_ID} />
        )}
        {activeSection === 'emergencias' && <EmergencyManagementScreen />}
      </main>
    </div>
  );
}
