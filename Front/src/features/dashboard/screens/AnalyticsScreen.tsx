import { useCallback, useEffect, useState } from 'react';
import { RefreshCw, X } from 'lucide-react';
import {
  useAuditLog,
  useRecommendations,
  useResolveRecommendation,
} from '@/hooks/useAnalytics';
import type { ConfigurationRecommendationDTO } from '@/features/dashboard/types';

function formatDate(value: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleString('es-AR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function truncateId(id: string): string {
  return id.length >= 8 ? `${id.slice(0, 8)}…` : id;
}

function getStatusClasses(status: ConfigurationRecommendationDTO['status']): string {
  if (status === 'pending_review') return 'bg-amber-50 text-amber-700 border-amber-200';
  if (status === 'approved') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  return 'bg-red-50 text-red-700 border-red-200';
}

function getStatusLabel(status: ConfigurationRecommendationDTO['status']): string {
  if (status === 'pending_review') return 'Pendiente';
  if (status === 'approved') return 'Aprobada';
  return 'Rechazada';
}

interface RecDetailModalProps {
  recommendation: ConfigurationRecommendationDTO;
  onClose: () => void;
  onResolved: () => void;
}

function RecDetailModal({ recommendation, onClose, onResolved }: RecDetailModalProps) {
  const { isSubmitting, error, resolveRecommendation } = useResolveRecommendation();
  const [operatorId, setOperatorId] = useState('');
  const [justification, setJustification] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const isPending = recommendation.status === 'pending_review';

  const handleResolve = async (approved: boolean) => {
    if (!operatorId.trim()) {
      setFormError('El operador es obligatorio.');
      return;
    }
    if (!justification.trim()) {
      setFormError('La justificación es obligatoria.');
      return;
    }
    setFormError(null);
    const result = await resolveRecommendation(
      recommendation.id,
      approved,
      operatorId.trim(),
      justification.trim()
    );
    if (result) onResolved();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-3 bg-slate-50 border-b border-slate-200 sticky top-0">
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-slate-800">Detalle de Recomendación</h3>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getStatusClasses(recommendation.status)}`}>
              {getStatusLabel(recommendation.status)}
            </span>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-200 text-slate-500">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-xs text-slate-400">Tipo</div>
              <div className="text-slate-700 capitalize">{recommendation.recommendation_type.replace(/_/g, ' ')}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Entidad objetivo</div>
              <div className="text-slate-700">{recommendation.target_entity_type}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Confianza</div>
              <div className="text-slate-700">{(recommendation.recommendation_confidence ?? 0).toFixed(2)}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Generada</div>
              <div className="text-slate-700">{formatDate(recommendation.generated_at)}</div>
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-400 mb-1">Cambio propuesto</div>
            <p className="text-sm text-slate-700 bg-slate-50 border border-slate-200 rounded-lg p-3">
              {recommendation.proposed_change}
            </p>
          </div>

          {recommendation.supporting_metrics && (
            <div>
              <div className="text-xs text-slate-400 mb-1">Métricas de soporte</div>
              <pre className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg p-3 whitespace-pre-wrap font-mono">
                {JSON.stringify(recommendation.supporting_metrics, null, 2)}
              </pre>
            </div>
          )}

          {recommendation.historic_trace && (
            <div>
              <div className="text-xs text-slate-400 mb-1">Trazabilidad histórica</div>
              <pre className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg p-3 whitespace-pre-wrap font-mono">
                {JSON.stringify(recommendation.historic_trace, null, 2)}
              </pre>
            </div>
          )}

          {isPending && (
            <div className="space-y-3 border-t border-slate-200 pt-4">
              <div>
                <label className="block text-sm text-slate-700 font-medium mb-1">
                  Operador <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={operatorId}
                  onChange={(e) => setOperatorId(e.target.value)}
                  placeholder="ID del operador"
                  className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-700 font-medium mb-1">
                  Justificación <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  rows={3}
                  placeholder="Motivo de la decisión"
                  className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              {(formError || error) && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  {formError || error}
                </div>
              )}

              <div className="flex gap-2">
                <button
                  onClick={() => handleResolve(true)}
                  disabled={isSubmitting}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 rounded-lg text-sm disabled:opacity-50"
                >
                  {isSubmitting ? 'Resolviendo...' : 'Aprobar'}
                </button>
                <button
                  onClick={() => handleResolve(false)}
                  disabled={isSubmitting}
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white font-medium py-2 rounded-lg text-sm disabled:opacity-50"
                >
                  {isSubmitting ? 'Resolviendo...' : 'Rechazar'}
                </button>
              </div>
            </div>
          )}

          {!isPending && recommendation.resolved_by && (
            <div className="border-t border-slate-200 pt-4 text-sm text-slate-600">
              <div>
                <span className="text-slate-400">Resuelto por:</span> {recommendation.resolved_by}
              </div>
              <div className="mt-1">
                <span className="text-slate-400">Fecha:</span> {formatDate(recommendation.resolved_at)}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function AnalyticsScreen() {
  const {
    recommendations,
    isLoading: recsLoading,
    error: recsError,
    fetchRecommendations,
  } = useRecommendations();
  const { entries, isLoading: auditLoading, error: auditError, fetchAuditLog } = useAuditLog();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  const selectedRec = recommendations.find((r) => r.id === selectedId) ?? null;

  useEffect(() => {
    fetchRecommendations();
  }, [fetchRecommendations]);

  useEffect(() => {
    if (selectedId) fetchAuditLog(selectedId);
  }, [selectedId, fetchAuditLog]);

  const handleOpenDetail = useCallback((rec: ConfigurationRecommendationDTO) => {
    setSelectedId(rec.id);
    setShowModal(true);
  }, []);

  return (
    <main className="max-w-5xl mx-auto space-y-6">
      <div className="flex justify-end">
        <button
          onClick={() => {
            fetchRecommendations();
            if (selectedId) fetchAuditLog(selectedId);
          }}
          disabled={recsLoading}
          className="flex items-center gap-1 text-sm px-3 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-600 font-medium disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${recsLoading ? 'animate-spin' : ''}`} />
          {recsLoading ? 'Cargando...' : 'Actualizar'}
        </button>
      </div>

      {recsError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{recsError}</div>
      )}

      <section className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <h2 className="font-bold text-slate-800">Recomendaciones de Configuración</h2>
          <span className="text-xs text-slate-400">{recommendations.length} recomendaciones</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="px-5 py-2 font-medium">ID</th>
                <th className="px-5 py-2 font-medium">Tipo</th>
                <th className="px-5 py-2 font-medium">Entidad</th>
                <th className="px-5 py-2 font-medium">Estado</th>
                <th className="px-5 py-2 font-medium">Generada</th>
                <th className="px-5 py-2 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {recommendations.length === 0 && !recsLoading && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-slate-400 italic">
                    Sin recomendaciones registradas.
                  </td>
                </tr>
              )}
              {recommendations.map((rec) => (
                <tr key={rec.id} className="border-b border-slate-100">
                  <td className="px-5 py-2 text-slate-600 font-mono" title={rec.id}>
                    {truncateId(rec.id)}
                  </td>
                  <td className="px-5 py-2 text-slate-700 capitalize">
                    {rec.recommendation_type.replace(/_/g, ' ')}
                  </td>
                  <td className="px-5 py-2 text-slate-700">{rec.target_entity_type}</td>
                  <td className="px-5 py-2">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getStatusClasses(rec.status)}`}>
                      {getStatusLabel(rec.status)}
                    </span>
                  </td>
                  <td className="px-5 py-2 text-slate-600">{formatDate(rec.generated_at)}</td>
                  <td className="px-5 py-2">
                    <button
                      onClick={() => handleOpenDetail(rec)}
                      className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-600 font-medium px-3 py-1.5 rounded-lg"
                    >
                      Ver Detalle
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {selectedRec && (
        <section className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
            <h2 className="font-bold text-slate-800">Registro de Auditoría</h2>
            <span className="text-xs text-slate-400 font-mono">{truncateId(selectedRec.id)}</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b border-slate-200">
                  <th className="px-5 py-2 font-medium">Acción</th>
                  <th className="px-5 py-2 font-medium">Fecha</th>
                  <th className="px-5 py-2 font-medium">Operador</th>
                  <th className="px-5 py-2 font-medium">Justificación</th>
                </tr>
              </thead>
              <tbody>
                {auditError && (
                  <tr>
                    <td colSpan={4} className="px-5 py-4 text-sm text-red-700">{auditError}</td>
                  </tr>
                )}
                {!auditError && entries.length === 0 && !auditLoading && (
                  <tr>
                    <td colSpan={4} className="px-5 py-8 text-center text-slate-400 italic">
                      Sin entradas de auditoría para esta recomendación.
                    </td>
                  </tr>
                )}
                {entries.map((entry) => (
                  <tr key={entry.id} className="border-b border-slate-100">
                    <td className="px-5 py-2 text-slate-700 capitalize">{entry.action}</td>
                    <td className="px-5 py-2 text-slate-600">{formatDate(entry.timestamp)}</td>
                    <td className="px-5 py-2 text-slate-600">{entry.operator_id || '—'}</td>
                    <td className="px-5 py-2 text-slate-600">{entry.justification || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {showModal && selectedRec && (
        <RecDetailModal
          recommendation={selectedRec}
          onClose={() => setShowModal(false)}
          onResolved={() => {
            setShowModal(false);
            fetchRecommendations();
            if (selectedId) fetchAuditLog(selectedId);
          }}
        />
      )}
    </main>
  );
}