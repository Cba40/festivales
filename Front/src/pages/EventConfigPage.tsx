import { PredictionsDashboard } from '../components/context-engine/PredictionsDashboard';
import { EVENT_ID } from '../components/context-engine/constants';
import { Card } from '../features/dashboard/components/ui';

export function EventConfigPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-4">
      <Card variant="standard">
        <PredictionsDashboard eventId={EVENT_ID} />
      </Card>
    </div>
  );
}