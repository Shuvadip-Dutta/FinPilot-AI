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
      badge: 'bg-slate-800 text-slate-300 border-slate-700',
      dot: 'bg-slate-400',
    },
    neutral: {
      badge: 'bg-slate-800/80 text-slate-300 border-slate-700/60',
      dot: 'bg-slate-400',
    },
    success: {
      badge: 'bg-emerald-950/60 text-emerald-400 border-emerald-800/50',
      dot: 'bg-emerald-400',
    },
    warning: {
      badge: 'bg-amber-950/60 text-amber-400 border-amber-800/50',
      dot: 'bg-amber-400',
    },
    danger: {
      badge: 'bg-rose-950/60 text-rose-400 border-rose-800/50',
      dot: 'bg-rose-400',
    },
    info: {
      badge: 'bg-cyan-950/60 text-cyan-400 border-cyan-800/50',
      dot: 'bg-cyan-400',
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
