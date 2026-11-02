import type { StatCardMetricDto, StatCardTone } from '../../../dtos/dashboard.dto';
import { Card, Icon } from '../../../components/ui';

export interface StatCardProps {
  metric: StatCardMetricDto;
}

const TONE_BADGE_CLASSES: Record<StatCardTone, string> = {
  lavender: 'bg-brand-100 text-brand-700',
  cyan: 'bg-status-infoBg text-brand-800',
  peach: 'bg-status-warningBg text-brand-700',
  rose: 'bg-status-dangerBg text-brand-700',
};

export function StatCard({ metric }: StatCardProps) {
  const isPositive = metric.trendDirection === 'up';

  return (
    <Card
      padding="sm"
      className="flex items-center gap-4 rounded-card bg-surface-card px-4 py-4 shadow-card transition-transform hover:-translate-y-0.5"
    >
      <div
        aria-hidden="true"
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-badge ${TONE_BADGE_CLASSES[metric.tone]}`}
      >
        <Icon name={metric.icon} className="text-sm" />
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-[11px] font-medium text-ink-muted">{metric.label}</p>
        <p className="mt-0.5 text-lg font-extrabold tracking-tight text-ink-primary">
          {metric.formattedValue}
        </p>
        <div className="mt-0.5 flex items-center gap-1 text-[11px] font-semibold text-ink-muted">
          <Icon
            name={isPositive ? 'arrow-trend-up' : 'arrow-trend-down'}
            className={`text-[10px] ${
              isPositive ? 'text-status-successText' : 'text-status-dangerText'
            }`}
          />
          <span>{metric.formattedDelta}</span>
        </div>
      </div>
    </Card>
  );
}
