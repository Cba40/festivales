import { useState } from 'react';
import { ZoneAdminScreen } from './ZoneAdminScreen';
import { EventReferencePointScreen } from './EventReferencePointScreen';
import { ExitManagementScreen } from './ExitManagementScreen';
import { TransportManagementScreen } from './TransportManagementScreen';
import { AccommodationManagementScreen } from './AccommodationManagementScreen';
import { EmergencyManagementScreen } from './EmergencyManagementScreen';
import { ProtocolManagementScreen } from './ProtocolManagementScreen';
import { DashboardHeader } from '../components/DashboardHeader';

const DEFAULT_EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

type Section = 'zones' | 'reference' | 'salidas' | 'transporte' | 'hospedaje' | 'emergencias' | 'protocolos';

const SECTIONS: { key: Section; label: string }[] = [
  { key: 'zones', label: 'Zonas' },
  { key: 'reference', label: 'Referencia Operativa' },
  { key: 'salidas', label: 'Salidas y Destinos' },
  { key: 'transporte', label: 'Transporte' },
  { key: 'hospedaje', label: 'Hospedaje' },
  { key: 'emergencias', label: 'Emergencias' },
  { key: 'protocolos', label: 'Protocolos de Emergencia' },
];

export function InfrastructureScreen() {
  const [activeSection, setActiveSection] = useState<Section>('zones');

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <DashboardHeader title="Gestión de Zonas" />
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
        {activeSection === 'protocolos' && <ProtocolManagementScreen />}
      </main>
    </div>
  );
}
