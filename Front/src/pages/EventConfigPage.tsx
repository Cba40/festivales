import { PredictionsDashboard } from '../components/context-engine/PredictionsDashboard';
import { EVENT_ID } from '../components/context-engine/constants';

export function EventConfigPage() {
  return (
    <div className="max-w-7xl mx-auto space-y-4">
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <PredictionsDashboard eventId={EVENT_ID} />
      </div>
    </div>
  );
}