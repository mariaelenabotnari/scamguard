import React from 'react';

export type CardTone = 'default' | 'banner' | 'chart' | 'muted' | 'panel';
export type CardPadding = 'none' | 'sm' | 'md' | 'lg';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  tone?: CardTone;
  padding?: CardPadding;
}

const TONE_STYLES: Record<CardTone, string> = {
  default: 'bg-surface-card shadow-card',
  banner: 'bg-surface-banner',
  chart: 'bg-surface-chart',
  muted: 'bg-surface-muted',
  panel: 'bg-surface-panel',
};

const PADDING_STYLES: Record<CardPadding, string> = {
  none: 'p-0',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export function Card({
  tone = 'default',
  padding = 'md',
  className = '',
  children,
  ...rest
}: CardProps) {
  return (
    <div
      className={`rounded-card text-ink-primary ${TONE_STYLES[tone]} ${PADDING_STYLES[padding]} ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}

export interface CardHeaderProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export function CardHeader({ title, subtitle, action, className = '' }: CardHeaderProps) {
  return (
    <div className={`mb-4 flex items-start justify-between gap-4 ${className}`}>
      <div>
        <h3 className="text-base font-bold text-ink-primary">{title}</h3>
        {subtitle ? <p className="mt-0.5 text-xs font-medium text-ink-muted">{subtitle}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
