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
    outline: 'bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200 hover:border-primary hover:text-primary active:scale-[0.98]',
    ghost: 'bg-transparent text-slate-500 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 active:scale-[0.98]'
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

type ColorScheme = 'emergency' | 'primary' | 'exit' | 'transport' | 'food' | 'lodging' | 'info';

interface QuickActionProps {
  label: string;
  icon: LucideIcon;
  onClick?: () => void;
  colorScheme?: ColorScheme;
}

export const QuickAction = ({ 
  label, 
  icon: Icon, 
  onClick,
  colorScheme = 'primary'
}: QuickActionProps) => {
  const colorConfig = {
    emergency: { bg: 'bg-danger/10', text: 'text-danger', hover: 'group-hover:bg-danger/20' },
    primary: { bg: 'bg-primary/10', text: 'text-primary', hover: 'group-hover:bg-primary/20' },
    exit: { bg: 'bg-warning/10', text: 'text-warning', hover: 'group-hover:bg-warning/20' },
    transport: { bg: 'bg-blue-100 dark:bg-blue-900/40', text: 'text-blue-600 dark:text-blue-400', hover: 'group-hover:bg-blue-200 dark:group-hover:bg-blue-800/40' },
    food: { bg: 'bg-success/10', text: 'text-success', hover: 'group-hover:bg-success/20' },
    lodging: { bg: 'bg-purple-100 dark:bg-purple-900/40', text: 'text-purple-600 dark:text-purple-400', hover: 'group-hover:bg-purple-200 dark:group-hover:bg-purple-800/40' },
    info: { bg: 'bg-slate-100 dark:bg-slate-700', text: 'text-slate-600 dark:text-slate-300', hover: 'group-hover:bg-slate-200 dark:group-hover:bg-slate-600' },
  };

  const colors = colorConfig[colorScheme];

  return (
    <button 
      onClick={onClick}
      className="flex flex-col items-center gap-2 group p-2 active:scale-95 transition-transform"
    >
      <div className={`w-16 h-16 rounded-2xl ${colors.bg} flex items-center justify-center ${colors.text} ${colors.hover} transition-all duration-300 group-active:scale-90 border-2 border-current border-opacity-20`}>
        <Icon size={32} strokeWidth={2} />
      </div>
      <span className="text-[11px] font-bold uppercase text-slate-700 dark:text-slate-300 tracking-tighter text-center leading-tight max-w-[60px]">
        {label}
      </span>
    </button>
  );
};
