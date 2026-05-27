import { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAppStore } from '../../core/state/store';

interface ProtectedRouteProps {
  children: ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { auth } = useAppStore();

  if (!auth.isAuthenticated) {
    return <Navigate to="/dashboard/login" replace />;
  }

  return <>{children}</>;
}
