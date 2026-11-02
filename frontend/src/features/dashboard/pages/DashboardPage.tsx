import { useState } from 'react';
import { AppShell } from '../../../components/layout';
import { Button, Card, CardHeader, EmptyState, Skeleton, Tabs } from '../../../components/ui';
import type { TimeRangeOption } from '../../../dtos/layout.dto';
import type { IDashboardService } from '../../../services/dashboard.service';
import { OverviewBanner } from '../components/OverviewBanner';
import { StatCardsGrid } from '../components/StatCardsGrid';
import { useDashboardOverview } from '../hooks/useDashboardOverview';

export interface DashboardPageProps {
  service?: IDashboardService;
}

const RANGE_TABS: readonly { value: TimeRangeOption; label: string }[] = [
  { value: '24h', label: '24h' },
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
];

export function DashboardPage({ service }: DashboardPageProps) {
  const [selectedRange, setSelectedRange] = useState<TimeRangeOption>('7d');
  const { data, isLoading, error, reload } = useDashboardOverview(selectedRange, service);

  return (
    <AppShell selectedRange={selectedRange} onRangeChange={setSelectedRange}>
      <div className="flex h-full flex-col justify-between gap-6">
        {isLoading ? (
          <div aria-label="Loading dashboard overview" className="space-y-6">
            <Skeleton variant="block" className="h-32 w-full" />
            <Skeleton variant="block" className="h-64 w-full" />
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <Skeleton variant="block" className="h-24 w-full" />
              <Skeleton variant="block" className="h-24 w-full" />
              <Skeleton variant="block" className="h-24 w-full" />
              <Skeleton variant="block" className="h-24 w-full" />
            </div>
          </div>
        ) : error ? (
          <EmptyState
            icon="triangle-exclamation"
            title="Unable to Load Dashboard Overview"
            description={error}
            action={
              <Button variant="primary" size="sm" leftIcon="rotate-right" onClick={reload}>
                Retry
              </Button>
            }
          />
        ) : data ? (
          <>
            {/* Top Hero Greeting Banner */}
            <OverviewBanner banner={data.banner} />

            {/* Center Activity Timeline Section (full chart added in feat/fe-timeline-chart) */}
            <Card tone="chart" className="flex-1">
              <CardHeader
                title="Coordination Activity Growth"
                subtitle="Overall Information"
                action={
                  <Tabs
                    ariaLabel="Timeline range switcher"
                    items={RANGE_TABS}
                    value={selectedRange}
                    onChange={setSelectedRange}
                  />
                }
              />
              <div className="flex h-48 items-center justify-center rounded-badge border border-brand-200/70 bg-surface-card/40 px-4 text-center text-xs font-medium text-ink-muted">
                Activity timeline for {selectedRange} window ({data.banner.activeChannelsCount}{' '}
                channels monitored • Parameter {data.banner.parameterVersion})
              </div>
            </Card>

            {/* Bottom 4 KPI Stat Cards Grid */}
            <StatCardsGrid stats={data.stats} />
          </>
        ) : null}
      </div>
    </AppShell>
  );
}

