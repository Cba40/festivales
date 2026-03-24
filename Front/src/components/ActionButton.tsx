import { ReactNode } from 'react';

interface ActionButtonProps {
  icon: ReactNode;
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
  size?: 'large' | 'small';
}

export const ActionButton = ({
  icon,
  label,
  onClick,
  variant = 'primary',
  size = 'large',
}: ActionButtonProps) => {
  const baseClasses = 'rounded-xl font-bold transition-all active:scale-95 shadow-lg';

  const variantClasses = {
    primary: 'bg-[#1e3a8a] text-white hover:bg-[#1e3a8a]/90',
    secondary: 'bg-gray-100 text-gray-800 hover:bg-gray-200',
  };

  const sizeClasses = {
    large: 'px-8 py-6 text-lg',
    small: 'px-4 py-3 text-sm',
  };

  return (
    <button
      onClick={onClick}
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} flex items-center justify-center gap-3 w-full`}
    >
      <span className="text-2xl">{icon}</span>
      <span>{label}</span>
    </button>
  );
};

interface QuickActionProps {
  emoji: string;
  label: string;
  onClick: () => void;
}

export const QuickAction = ({ emoji, label, onClick }: QuickActionProps) => {
  return (
    <button
      onClick={onClick}
      className="bg-white rounded-lg p-4 shadow-md hover:shadow-lg transition-all active:scale-95 flex flex-col items-center gap-2"
    >
      <span className="text-3xl">{emoji}</span>
      <span className="text-xs font-semibold text-gray-800">{label}</span>
    </button>
  );
};
