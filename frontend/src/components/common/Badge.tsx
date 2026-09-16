import React from 'react';
import { StatusVariant } from '../../types/common';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: StatusVariant;
  size?: 'sm' | 'md';
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'sm',
  dot = false,
  className = '',
  ...props
}) => {
  const variantStyles: Record<StatusVariant, { badge: string; dot: string }> = {
    default: {
      badge: 'bg-surface-secondary text-text-secondary border-border-theme',
      dot: 'bg-text-muted',
    },
    neutral: {
      badge: 'bg-surface-secondary/80 text-text-secondary border-border-theme/60',
      dot: 'bg-text-muted',
    },
    success: {
      badge: 'bg-status-positive-soft text-status-positive border-status-positive/30',
      dot: 'bg-status-positive',
    },
    warning: {
      badge: 'bg-status-warning-soft text-status-warning border-status-warning/30',
      dot: 'bg-status-warning',
    },
    danger: {
      badge: 'bg-status-negative-soft text-status-negative border-status-negative/30',
      dot: 'bg-status-negative',
    },
    info: {
      badge: 'bg-status-info-soft text-status-info border-status-info/30',
      dot: 'bg-status-info',
    },
  };

  const sizeStyles = {
    sm: 'text-[11px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
  };

  const style = variantStyles[variant];

  return (
    <span
      className={`inline-flex items-center font-medium rounded-md border whitespace-nowrap gap-1.5 ${sizeStyles[size]} ${style.badge} ${className}`}
      {...props}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${style.dot} shrink-0`} />}
      <span>{children}</span>
    </span>
  );
};
