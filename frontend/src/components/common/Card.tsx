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
      className={`bg-slate-900/70 border border-slate-800/90 rounded-xl backdrop-blur-xs shadow-sm overflow-hidden flex flex-col ${className}`}
      {...props}
    >
      {(title || subtitle || action) && (
        <div className={`flex items-start justify-between border-b border-slate-800/80 ${compact ? 'px-4 py-3' : 'px-6 py-4'}`}>
          <div>
            {title && (
              <h3 className="text-sm font-semibold text-slate-100 tracking-wide">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>
            )}
          </div>
          {action && <div className="ml-4 shrink-0">{action}</div>}
        </div>
      )}

      <div className={`flex-1 ${paddingClass}`}>{children}</div>

      {footer && (
        <div
          className={`border-t border-slate-800/80 bg-slate-950/40 ${
            compact ? 'px-4 py-2.5' : 'px-6 py-3.5'
          }`}
        >
          {footer}
        </div>
      )}
    </div>
  );
};
