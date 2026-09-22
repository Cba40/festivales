import { useMemo, useState } from 'react';
import { Info, AlertTriangle, X } from 'lucide-react';
import { usePublicAlerts } from '@/features/public/hooks/usePublicAlerts';
import type { AlertType, MessagePriority } from '@/features/dashboard/types';

const DEFAULT_EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

interface Notice {
  key: string;
  style: AlertType;
  label: string;
  isMunicipal: boolean;
  title: string;
  body: string;
}

const ALERT_META: Record<AlertType, { label: string; styles: string }> = {
  info: {
    label: 'Información',
    styles:
      'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-100',
  },
  warning: {
    label: 'Aviso',
    styles:
      'bg-amber-100 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-100',
  },
  disruption: {
    label: 'Interrupción',
    styles:
      'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-800 dark:text-red-100',
  },
  closure: {
    label: 'Clausura',
    styles:
      'bg-slate-100 dark:bg-slate-700/40 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200',
  },
};

const PRIORITY_TO_ALERT: Record<MessagePriority, AlertType> = {
  normal: 'info',
  high: 'warning',
  urgent: 'disruption',
};

const PRIORITY_LABELS: Record<MessagePriority, string> = {
  normal: 'Informativo',
  high: 'Alta prioridad',
  urgent: 'Urgente',
};

const styleSeverity = (style: AlertType): number => {
  const order: Record<AlertType, number> = {
    disruption: 0,
    closure: 1,
    warning: 2,
    info: 3,
  };
  return order[style];
};

interface PublicAlertsBannerProps {
  eventId?: string;
  className?: string;
}

const PublicAlertsBanner = ({ eventId = DEFAULT_EVENT_ID, className }: PublicAlertsBannerProps) => {
  const { data } = usePublicAlerts(eventId);
  const [dismissed, setDismissed] = useState<string[]>([]);

  const notices = useMemo<Notice[]>(() => {
    if (!data) return [];
    const alertNotices: Notice[] = data.alerts.map((a) => ({
      key: `a-${a.id}`,
      style: a.alert_type,
      label: ALERT_META[a.alert_type]?.label ?? 'Información',
      isMunicipal: false,
      title: a.title,
      body: a.description,
    }));
    const messageNotices: Notice[] = data.messages.map((m) => {
      const style = PRIORITY_TO_ALERT[m.priority] ?? 'info';
      return {
        key: `m-${m.id}`,
        style,
        label: PRIORITY_LABELS[m.priority] ?? 'Informativo',
        isMunicipal: true,
        title: m.title,
        body: m.description,
      };
    });
    return [...alertNotices, ...messageNotices].sort(
      (x, y) => styleSeverity(x.style) - styleSeverity(y.style)
    );
  }, [data]);

  const visible = notices.filter((n) => !dismissed.includes(n.key));

  if (visible.length === 0) return null;

  const containerClass =
    className ?? 'px-4 pt-3 space-y-2 w-full max-w-2xl mx-auto';

  return (
    <div className={containerClass}>
      {visible.map((notice) => {
        const Icon = notice.style === 'info' ? Info : AlertTriangle;
        return (
          <div
            key={notice.key}
            className={`flex items-start gap-3 rounded-xl border p-3 shadow-sm ${ALERT_META[notice.style]?.styles ?? ALERT_META.info.styles}`}
          >
            <Icon size={18} className="mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wide">
                  {notice.label}
                </span>
                {notice.isMunicipal && (
                  <span className="text-[10px] font-semibold uppercase">· Municipal</span>
                )}
              </div>
              <h3 className="text-sm font-bold line-clamp-1">{notice.title}</h3>
              <p className="text-xs mt-0.5 line-clamp-2">{notice.body}</p>
            </div>
            <button
              onClick={() => setDismissed((prev) => [...prev, notice.key])}
              className="p-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 transition-colors shrink-0"
              aria-label="Descartar aviso"
            >
              <X size={16} />
            </button>
          </div>
        );
      })}
    </div>
  );
};

export default PublicAlertsBanner;