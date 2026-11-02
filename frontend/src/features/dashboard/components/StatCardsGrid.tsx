import type { StatCardMetricDto } from '../../../dtos/dashboard.dto';
import { EmptyState } from '../../../components/ui';
import { StatCard } from './StatCard';

export interface StatCardsGridProps {
  stats: readonly StatCardMetricDto[];
}

export function StatCardsGrid({ stats }: StatCardsGridProps) {
  if (stats.length === 0) {
    return (
      <EmptyState
        icon="chart-pie"
        title="No KPI Metrics Available"
        description="No channel or cluster statistics were recorded for the selected time window."
      />
    );
  }

  return (
    <section
      aria-label="Key coordination metrics"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
    >
      {stats.map((metric) => (
        <StatCard key={metric.id} metric={metric} />
      ))}
    </section>
  );
}
