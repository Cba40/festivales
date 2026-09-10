import type { ReactNode } from 'react';

export type CardVariant = 'standard' | 'action' | 'metric' | 'state';

export interface CardProps {
  variant?: CardVariant;
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}

const BASE_CLASSES = 'bg-white border border-slate-200 rounded-xl shadow-sm';

const VARIANT_CLASSES: Record<CardVariant, string> = {
  standard: 'p-5',
  action:
    'p-5 hover:shadow-md hover:border-indigo-300 hover:-translate-y-0.5 transition-all cursor-pointer text-left',
  metric: 'p-5',
  state: 'p-5',
};

export function Card({ variant = 'standard', children, className, onClick }: CardProps) {
  const classes = [BASE_CLASSES, VARIANT_CLASSES[variant], className].filter(Boolean).join(' ');

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={classes}>
        {children}
      </button>
    );
  }

  return <div className={classes}>{children}</div>;
}