import { PredictionsDashboard } from '../components/context-engine/PredictionsDashboard';
import { useResolvedEventId } from '../hooks/useActiveEvent';
import { Card } from '../features/dashboard/components/ui';

export function EventConfigPage() {
  // Evento activo del store global (`useActiveEvent`), no `VITE_EVENT_ID`.
  // No se pasa a `PredictionsDashboard` porque ya resuelve el mismo store por su
  // cuenta: hacerlo explícito sólo congelaría el valor del primer render.
  useResolvedEventId();

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      <Card variant="standard">
        <PredictionsDashboard />
      </Card>
    </div>
  );
}