import React from 'react';
import { Button } from './Button';
import { FolderOpen } from 'lucide-react';

export interface EmptyStateProps {
  icon?: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = FolderOpen,
  title,
  description,
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center bg-surface-secondary/40 border border-dashed border-border-theme rounded-xl my-4 ${className}`}
    >
      <div className="w-12 h-12 rounded-xl bg-surface border border-border-theme flex items-center justify-center text-text-muted mb-4 shadow-xs">
        <Icon className="w-6 h-6 text-accent-primary" />
      </div>
      <h4 className="text-base font-semibold text-text-primary mb-1.5">{title}</h4>
      <p className="text-sm text-text-muted max-w-sm mb-5 leading-relaxed">
        {description}
      </p>
      {actionLabel && onAction && (
        <Button variant="primary" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
