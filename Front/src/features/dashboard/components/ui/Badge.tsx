import type { ReactNode } from 'react';

export type BadgeVariant = 'success' | 'warning' | 'error' | 'info' | 'neutral';

export interface BadgeProps {
  variant: BadgeVariant;
  children: ReactNode;
  className?: string;
}

const BASE_CLASSES =
  'text-[10px] font-bold px-2 py-0.5 rounded-full border inline-flex items-center gap-1';

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  error: 'bg-red-50 text-red-700 border-red-200',
  info: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  neutral: 'bg-slate-100 text-slate-600 border-slate-200',
};

export function Badge({ variant, children, className }: BadgeProps) {
  return (
    <span className={[BASE_CLASSES, VARIANT_CLASSES[variant], className].filter(Boolean).join(' ')}>
      {children}
    </span>
  );
}