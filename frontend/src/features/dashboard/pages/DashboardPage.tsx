import { useState } from 'react';
import { AppShell } from '../../../components/layout';
import { Button, EmptyState, Skeleton } from '../../../components/ui';
import type { TimeRangeOption } from '../../../dtos/layout.dto';
import type { IDashboardService } from '../../../services/dashboard.service';
import { ActivityTimelineChart } from '../components/ActivityTimelineChart';
import { NarrativeDistributionChart } from '../components/NarrativeDistributionChart';
import { NeedsAttentionSection } from '../components/NeedsAttentionSection';
import { OverviewBanner } from '../components/OverviewBanner';
import { StatCardsGrid } from '../components/StatCardsGrid';
import { SystemStatusWidget } from '../components/SystemStatusWidget';
import { useDashboardOverview } from '../hooks/useDashboardOverview';

export interface DashboardPageProps {
  service?: IDashboardService;
}

export function DashboardPage({ service }: DashboardPageProps) {
  const [selectedRange, setSelectedRange] = useState<TimeRangeOption>('7d');
  const { data, isLoading, error, reload } = useDashboardOverview(selectedRange, service);

  return (
    <AppShell selectedRange={selectedRange} onRangeChange={setSelectedRange}>
      <div className="flex h-full flex-col gap-6">
        {isLoading ? (
          <div aria-label="Loading dashboard overview" className="space-y-6">
            <Skeleton variant="block" className="h-16 w-full" />
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <Skeleton variant="block" className="h-24 w-full" />
              <Skeleton variant="block" className="h-24 w-full" />
              <Skeleton variant="block" className="h-24 w-full" />
              <Skeleton variant="block" className="h-24 w-full" />
            </div>
            <Skeleton variant="block" className="h-64 w-full" />
            <Skeleton variant="block" className="h-64 w-full" />
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
            {/* Top Compact Page Header */}
            <OverviewBanner banner={data.banner} />

            {/* Top 4 KPI Stat Cards */}
            <StatCardsGrid stats={data.stats} />

            {/* Two-Column Block: Needs Attention */}
            <NeedsAttentionSection
              topClusters={data.topClusters}
              riskiestChannels={data.riskiestChannels}
            />

            {/* Main Activity Timeline Chart */}
            <ActivityTimelineChart timeline={data.timeline} />

            {/* Bottom Row: Narrative Distribution & System Status */}
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              <NarrativeDistributionChart narratives={data.narrativeCounts} />
              <SystemStatusWidget systemStatus={data.systemStatus} />
            </div>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
