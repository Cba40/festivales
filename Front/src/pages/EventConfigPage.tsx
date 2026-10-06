import { PredictionsDashboard } from '../components/context-engine/PredictionsDashboard';
import { useAppStore } from '../core/state/store';
import { Card } from '../features/dashboard/components/ui';

export function EventConfigPage() {
  // Suscripción al store global (`useActiveEvent`), no `VITE_EVENT_ID`. No se pasa
  // a `PredictionsDashboard` porque ya resuelve el mismo store por su cuenta:
  // hacerlo explícito sólo congelaría el valor del primer render.
  useAppStore((s) => s.activeEventId);

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      <Card variant="standard">
        <PredictionsDashboard />
      </Card>
    </div>
  );
}