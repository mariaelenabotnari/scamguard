import React from 'react';
import { Icon, type IconName } from './Icon';

export type BadgeVariant = 'neutral' | 'brand' | 'low' | 'medium' | 'high' | 'success';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  icon?: IconName;
  onDismiss?: () => void;
}

const BADGE_STYLES: Record<BadgeVariant, string> = {
  neutral: 'bg-brand-200/70 text-ink-secondary',
  brand: 'bg-brand-100 text-brand-700',
  low: 'bg-status-infoBg text-status-infoText',
  medium: 'bg-status-warningBg text-status-warningText',
  high: 'bg-status-dangerBg text-status-dangerText',
  success: 'bg-status-successBg text-status-successText',
};

export function Badge({
  variant = 'neutral',
  icon,
  onDismiss,
  className = '',
  children,
  ...rest
}: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${BADGE_STYLES[variant]} ${className}`}
      {...rest}
    >
      {icon ? <Icon name={icon} className="text-[11px]" /> : null}
      <span>{children}</span>
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Remove badge"
          className="ml-0.5 inline-flex h-4 w-4 items-center justify-center rounded-full hover:bg-black/10 focus-visible:outline-none"
        >
          <Icon name="xmark" className="text-[10px]" />
        </button>
      ) : null}
    </span>
  );
}
