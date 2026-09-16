import React from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium rounded-lg transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none disabled:shadow-none cursor-pointer select-none';

    const sizeStyles = {
      sm: 'text-xs px-3 py-1.5 gap-1.5',
      md: 'text-sm px-4 py-2 gap-2',
      lg: 'text-base px-6 py-3 gap-2.5',
    };

    const variantStyles = {
      primary:
        'bg-accent-primary hover:bg-accent-hover text-accent-text font-semibold shadow-xs active:opacity-90',
      secondary:
        'bg-surface-secondary hover:bg-surface text-text-primary border border-border-theme hover:border-accent-primary/40 active:opacity-90',
      outline:
        'border border-border-theme bg-transparent hover:bg-surface-secondary hover:border-accent-primary/50 text-text-primary active:bg-surface-secondary/80',
      ghost:
        'bg-transparent hover:bg-surface-secondary text-text-secondary hover:text-text-primary active:bg-surface-secondary/80',
      danger:
        'bg-status-negative hover:opacity-90 text-white shadow-xs active:opacity-80',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin text-current" />
        ) : (
          leftIcon
        )}
        <span>{children}</span>
        {!isLoading && rightIcon}
      </button>
    );
  }
);

Button.displayName = 'Button';
