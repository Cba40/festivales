import { useSearchParams } from 'react-router-dom';
import { MotorConfigScreen } from './MotorConfigScreen';
import { EventConfigPage } from '../../../pages/EventConfigPage';
import { ObservationsScreen } from './ObservationsScreen';
import { AnalyticsScreen } from './AnalyticsScreen';
import { DashboardHeader } from '../components/DashboardHeader';
import { SectionTabs } from '../components/ui';

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
  const tabParam = searchParams.get('tab') as Section | null;
  const activeSection: Section =
    tabParam && SECTION_KEYS.includes(tabParam) ? tabParam : 'config';

  const selectSection = (section: Section) => {
    setSearchParams({ tab: section });
  };

  return (
    <div className="min-h-screen bg-slate-50 w-full">
      <DashboardHeader title="Motor" subtitle="Configuración y Análisis del Motor" />
      <SectionTabs
        sections={SECTIONS}
        activeSection={activeSection}
        onChange={selectSection}
        className="flex flex-wrap gap-2 px-4 sm:px-6 py-3"
      />

      <main className="p-4 sm:p-6">
        {activeSection === 'config' && <MotorConfigScreen />}
        {activeSection === 'predictions' && <EventConfigPage />}
        {activeSection === 'observations' && <ObservationsScreen />}
        {activeSection === 'analytics' && <AnalyticsScreen />}
      </main>
    </div>
  );
}