import React, { useId } from 'react';
import { Icon } from './Icon';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: readonly SelectOption[];
  hint?: string;
  error?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, options, hint, error, className = '', id, ...rest }, ref) => {
    const generatedId = useId();
    const selectId = id ?? generatedId;

    return (
      <div className="flex flex-col gap-1.5">
        {label ? (
          <label htmlFor={selectId} className="text-xs font-semibold text-ink-primary">
            {label}
          </label>
        ) : null}
        <div className="relative flex items-center">
          <select
            ref={ref}
            id={selectId}
            aria-invalid={Boolean(error)}
            className={`h-10 w-full appearance-none rounded-badge border bg-surface-card pl-3.5 pr-9 text-sm font-medium text-ink-primary transition-colors focus:border-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-200 disabled:cursor-not-allowed disabled:bg-surface-muted ${
              error ? 'border-status-dangerText' : 'border-brand-200'
            } ${className}`}
            {...rest}
          >
            {options.map((opt) => (
              <option key={opt.value} value={opt.value} disabled={opt.disabled}>
                {opt.label}
              </option>
            ))}
          </select>
          <span className="pointer-events-none absolute right-3 text-ink-muted">
            <Icon name="chevron-down" className="text-xs" />
          </span>
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

Select.displayName = 'Select';
