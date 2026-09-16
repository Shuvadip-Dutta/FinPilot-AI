import React from 'react';
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Sparkles, Loader2 } from 'lucide-react';

export const ProtectedRoute: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-app flex flex-col items-center justify-center p-4">
        <div className="flex flex-col items-center gap-4 text-center max-w-sm">
          <div className="w-12 h-12 rounded-2xl bg-accent-primary flex items-center justify-center shadow-xs">
            <Sparkles className="w-6 h-6 text-accent-text stroke-[2.5]" />
          </div>
          <div className="flex items-center gap-2 text-accent-primary font-mono text-sm font-medium">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Verifying FinPilot JWT Session...</span>
          </div>
          <p className="text-xs text-text-muted">
            Validating authentication tokens with Django REST backend
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children ? <>{children}</> : <Outlet />;
};
