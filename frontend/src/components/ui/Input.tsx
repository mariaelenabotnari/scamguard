import React, { useId } from 'react';
import { Icon, type IconName } from './Icon';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  leftIcon?: IconName;
  rightElement?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, hint, error, leftIcon, rightElement, className = '', id, ...rest }, ref) => {
    const generatedId = useId();
    const inputId = id ?? generatedId;

    return (
      <div className="flex flex-col gap-1.5">
        {label ? (
          <label htmlFor={inputId} className="text-xs font-semibold text-ink-primary">
            {label}
          </label>
        ) : null}
        <div className="relative flex items-center">
          {leftIcon ? (
            <span className="pointer-events-none absolute left-3.5 text-ink-muted">
              <Icon name={leftIcon} className="text-sm" />
            </span>
          ) : null}
          <input
            ref={ref}
            id={inputId}
            aria-invalid={Boolean(error)}
            className={`h-10 w-full rounded-badge border bg-surface-card text-sm text-ink-primary placeholder:text-ink-muted transition-colors focus:border-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-200 disabled:cursor-not-allowed disabled:bg-surface-muted ${
              leftIcon ? 'pl-10' : 'pl-3.5'
            } ${rightElement ? 'pr-10' : 'pr-3.5'} ${
              error ? 'border-status-dangerText' : 'border-brand-200'
            } ${className}`}
            {...rest}
          />
          {rightElement ? <div className="absolute right-3">{rightElement}</div> : null}
        </div>
        {error ? (
          <p role="alert" className="text-xs font-medium text-status-dangerText">
            {error}
          </p>
        ) : hint ? (
          <p className="text-xs text-ink-muted">{hint}</p>
        ) : null}
      </div>
    );
  },
);

Input.displayName = 'Input';
