import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';
import { Badge } from './Badge';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  statusCode?: number;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message = 'FinPilot could not complete this request right now.',
  statusCode,
  onRetry,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center bg-rose-950/20 border border-rose-900/40 rounded-xl my-4 ${className}`}
      role="alert"
    >
      <div className="w-12 h-12 rounded-xl bg-rose-900/30 border border-rose-800/50 flex items-center justify-center text-rose-400 mb-4">
        <AlertTriangle className="w-6 h-6" />
      </div>

      <div className="flex items-center gap-2 mb-1.5">
        <h4 className="text-base font-semibold text-slate-200">{title}</h4>
        {statusCode && (
          <Badge variant="danger" size="sm">
            HTTP {statusCode}
          </Badge>
        )}
      </div>

      <p className="text-sm text-slate-400 max-w-md mb-5 leading-relaxed">
        {message}
      </p>

      {onRetry && (
        <Button
          variant="secondary"
          size="sm"
          onClick={onRetry}
          leftIcon={<RefreshCw className="w-4 h-4" />}
        >
          Try Again
        </Button>
      )}
    </div>
  );
};
