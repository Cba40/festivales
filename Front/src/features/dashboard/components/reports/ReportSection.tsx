import type { ReactNode } from 'react';
import { Card, RefreshButton } from '../ui';

interface ReportSectionProps {
  title: string;
  subtitle?: string;
  loading: boolean;
  error: string | null;
  hasData: boolean;
  emptyText: string;
  onRefresh: () => void;
  children?: ReactNode;
}

export function ReportSection({
  title,
  subtitle,
  loading,
  error,
  hasData,
  emptyText,
  onRefresh,
  children,
}: ReportSectionProps) {
  return (
    <Card variant="standard">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h2 className="font-bold text-slate-800">{title}</h2>
        <div className="flex items-center gap-2">
          {subtitle && <span className="text-xs text-slate-400">{subtitle}</span>}
          <RefreshButton onClick={onRefresh} loading={loading} />
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          <div>{error}</div>
          <button
            onClick={onRefresh}
            className="mt-2 text-xs font-medium underline text-red-700"
          >
            Reintentar
          </button>
        </div>
      )}

      {!error && loading && (
        <div className="p-10 text-center text-slate-500">Cargando informe...</div>
      )}

      {!error && !loading && !hasData && (
        <div className="py-8 text-center text-slate-400 italic">{emptyText}</div>
      )}

      {!error && !loading && hasData && children}
    </Card>
  );
}