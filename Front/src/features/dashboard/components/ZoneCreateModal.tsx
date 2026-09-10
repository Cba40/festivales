import { X } from 'lucide-react';
import { CreateZoneForm } from './CreateZoneForm';

interface ZoneCreateModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function ZoneCreateModal({ open, onClose, onSuccess }: ZoneCreateModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-800">Nueva Zona</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="text-slate-400 hover:text-slate-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6">
          <CreateZoneForm onSuccess={onSuccess} onCancel={onClose} />
        </div>
      </div>
    </div>
  );
}