import React from 'react';

export interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  footer?: React.ReactNode;
  compact?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  subtitle,
  action,
  footer,
  compact = false,
  className = '',
  ...props
}) => {
  const paddingClass = compact ? 'p-4' : 'p-6';

  return (
    <div
      className={`bg-surface border border-border-theme rounded-xl shadow-card transition-shadow duration-200 overflow-hidden flex flex-col ${className}`}
      {...props}
    >
      {(title || subtitle || action) && (
        <div className={`flex items-start justify-between border-b border-border-subtle ${compact ? 'px-4 py-3' : 'px-6 py-4'}`}>
          <div>
            {title && (
              <h3 className="text-sm font-semibold text-text-primary tracking-wide">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>
            )}
          </div>
          {action && <div className="ml-4 shrink-0">{action}</div>}
        </div>
      )}

      <div className={`flex-1 ${paddingClass}`}>{children}</div>

      {footer && (
        <div
          className={`border-t border-border-subtle bg-surface-secondary/40 ${
            compact ? 'px-4 py-2.5' : 'px-6 py-3.5'
          }`}
        >
          {footer}
        </div>
      )}
    </div>
  );
};
