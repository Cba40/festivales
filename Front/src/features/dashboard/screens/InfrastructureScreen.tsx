import { useState } from 'react';
import { ZoneAdminScreen } from './ZoneAdminScreen';
import { EventReferencePointScreen } from './EventReferencePointScreen';
import { ExitManagementScreen } from './ExitManagementScreen';
import { TransportManagementScreen } from './TransportManagementScreen';
import { AccommodationManagementScreen } from './AccommodationManagementScreen';
import { EmergencyManagementScreen } from './EmergencyManagementScreen';
import { ProtocolManagementScreen } from './ProtocolManagementScreen';
import { DashboardHeader } from '../components/DashboardHeader';
import { AppFooter } from '@/components/AppFooter';
import { SectionTabs } from '../components/ui';
import { useAppStore } from '@/core/state/store';

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
  // Evento activo del store global (`useActiveEvent`), no `VITE_EVENT_ID`.
  //
  // El corte va acá y no en cada hija. `ExitManagementScreen`,
  // `TransportManagementScreen` y `AccommodationManagementScreen` piden zonas,
  // líneas y destinos en el mount, y sus props son `eventId: string`. Al no
  // renderizarlas hasta tener un ID real, el compilador los vuelve `string` y esas
  // requests quedan imposible de despachar con el evento equivocado.
  const eventId = useAppStore((s) => s.activeEventId);

  if (!eventId) {
    return (
      <div className="min-h-screen bg-slate-50 w-full flex items-center justify-center">
        <p className="text-sm text-slate-500">Esperando el evento activo...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <DashboardHeader title="Gestión de Zonas" />
      <SectionTabs
        sections={SECTIONS}
        activeSection={activeSection}
        onChange={setActiveSection}
        className="flex flex-wrap gap-2 px-4 sm:px-6 py-3"
      />

      <main className="p-4 sm:p-6">
        {activeSection === 'zones' && <ZoneAdminScreen />}
        {activeSection === 'reference' && <EventReferencePointScreen />}
        {activeSection === 'salidas' && <ExitManagementScreen eventId={eventId} />}
        {activeSection === 'transporte' && (
          <TransportManagementScreen eventId={eventId} />
        )}
        {activeSection === 'hospedaje' && (
          <AccommodationManagementScreen eventId={eventId} />
        )}
        {activeSection === 'emergencias' && <EmergencyManagementScreen />}
        {activeSection === 'protocolos' && <ProtocolManagementScreen />}
      </main>

      <AppFooter variant="private" />
    </div>
  );
}
