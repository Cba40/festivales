interface AppFooterProps {
  variant?: 'public' | 'private';
}

export function AppFooter({ variant = 'public' }: AppFooterProps) {
  const className =
    variant === 'private'
      ? 'text-[10px] text-slate-400 dark:text-slate-500 text-center mt-auto pt-4'
      : 'text-xs text-slate-400 dark:text-slate-500 text-center mt-8 pb-4';

  return <p className={className}>Desarrollado por CBA 4.0</p>;
}

export default AppFooter;
