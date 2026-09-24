import type { LucideIcon } from 'lucide-react';

interface MetricMiniProps {
  icon: LucideIcon;
  label: string;
  value: string | number;
  sub?: string;
  accent: string;
  iconBg: string;
}

export function MetricMini({ icon: Icon, label, value, sub, accent, iconBg }: MetricMiniProps) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <span className={`flex items-center justify-center w-9 h-9 rounded-xl border ${iconBg}`}>
          <Icon className={`w-4 h-4 ${accent}`} />
        </span>
        <span className="text-2xl font-bold text-slate-800">{value}</span>
      </div>
      <div className="text-xs font-semibold text-slate-700">{label}</div>
      {sub && <p className="text-[10px] text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}