import React from 'react';
import { LucideIcon } from 'lucide-react';

interface ActionButtonProps {
  label: string;
  icon?: LucideIcon;
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  fullWidth?: boolean;
  className?: string;
  onClick?: () => void;
  badge?: string;
}

export const ActionButton = ({
  label,
  icon: Icon,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  className = '',
  onClick,
  badge
}: ActionButtonProps) => {
  
  const variants = {
    primary: 'bg-primary text-white shadow-lg shadow-primary/25 hover:bg-primary/90 active:scale-[0.98]',
    secondary: 'bg-slate-900 text-white hover:bg-slate-800 active:scale-[0.98]',
    outline: 'bg-white border-2 border-slate-200 text-slate-700 hover:border-primary hover:text-primary active:scale-[0.98]',
    ghost: 'bg-transparent text-slate-500 hover:bg-slate-50 active:scale-[0.98]'
  };

  const sizes = {
    sm: 'px-4 py-2 text-xs font-bold uppercase tracking-wider rounded-xl',
    md: 'px-6 py-4 text-sm font-black uppercase italic tracking-tight rounded-2xl',
    lg: 'px-8 py-5 text-base font-black uppercase italic tracking-tight rounded-3xl',
    xl: 'px-10 py-6 text-xl font-black uppercase italic tracking-tight rounded-[2rem]'
  };

  return (
    <button
      onClick={onClick}
      className={`
        relative flex items-center justify-center gap-3 transition-all duration-200
        ${variants[variant]}
        ${sizes[size]}
        ${fullWidth ? 'w-full' : ''}
        ${className}
      `}
    >
      {Icon && <Icon size={size === 'xl' ? 28 : 20} strokeWidth={2.5} />}
      <span>{label}</span>
      
      {badge && (
        <span className="absolute -top-2 -right-1 bg-danger text-white text-[10px] px-2 py-0.5 rounded-full ring-2 ring-white font-black animate-bounce">
          {badge}
        </span>
      )}
    </button>
  );
};

export const QuickAction = ({ 
  label, 
  icon: Icon, 
  onClick 
}: { 
  label: string; 
  icon: LucideIcon; 
  onClick?: () => void 
}) => (
  <button 
    onClick={onClick}
    className="flex flex-col items-center gap-2 group p-2"
  >
    <div className="w-14 h-14 rounded-2xl bg-slate-50 flex items-center justify-center text-slate-400 group-hover:bg-primary/10 group-hover:text-primary transition-all duration-300 group-active:scale-90 border border-slate-100">
      <Icon size={24} />
    </div>
    <span className="text-[10px] font-bold uppercase text-slate-500 tracking-tighter group-hover:text-primary transition-colors">
      {label}
    </span>
  </button>
);
