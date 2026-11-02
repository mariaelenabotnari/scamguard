import React from 'react';
import { Icon, type IconName } from './Icon';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  leftIcon?: IconName;
  rightIcon?: IconName;
  isLoading?: boolean;
}

const VARIANT_STYLES: Record<ButtonVariant, string> = {
  primary:
    'bg-brand-700 text-white hover:bg-brand-800 focus-visible:ring-brand-500 shadow-pill',
  secondary:
    'bg-surface-banner text-ink-primary hover:bg-brand-200 focus-visible:ring-brand-400',
  outline:
    'border border-brand-200 bg-surface-card text-ink-primary hover:bg-surface-muted focus-visible:ring-brand-400',
  ghost:
    'bg-transparent text-ink-secondary hover:bg-surface-muted hover:text-ink-primary focus-visible:ring-brand-300',
  danger:
    'bg-status-dangerBg text-status-dangerText hover:bg-rose-200 focus-visible:ring-rose-400',
};

const SIZE_STYLES: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs rounded-lg gap-1.5',
  md: 'h-10 px-4 text-sm rounded-badge gap-2',
  lg: 'h-12 px-6 text-base rounded-badge gap-2.5',
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      leftIcon,
      rightIcon,
      isLoading = false,
      disabled,
      className = '',
      children,
      type = 'button',
      ...rest
    },
    ref,
  ) => {
    const isDisabled = disabled || isLoading;

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        className={`inline-flex items-center justify-center font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 ${VARIANT_STYLES[variant]} ${SIZE_STYLES[size]} ${className}`}
        {...rest}
      >
        {isLoading ? (
          <Icon name="spinner" spin className="text-current" />
        ) : leftIcon ? (
          <Icon name={leftIcon} className="text-current" />
        ) : null}
        {children && <span>{children}</span>}
        {!isLoading && rightIcon ? <Icon name={rightIcon} className="text-current" /> : null}
      </button>
    );
  },
);

Button.displayName = 'Button';
