import { useState } from 'react';
import { AppShell } from '../../../components/layout';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Skeleton,
  Tabs,
} from '../../../components/ui';
import type { AlertSeverity } from '../../../dtos/alert.dto';
import type { IAlertService } from '../../../services/alert.service';
import { AlertCard } from '../components/AlertCard';
import { useAlertsFeed } from '../hooks/useAlertsFeed';

export interface AlertsPageProps {
  service?: IAlertService;
}

const SEVERITY_TABS: readonly { value: AlertSeverity | 'all'; label: string }[] = [
  { value: 'all', label: 'All Alerts' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

export function AlertsPage({ service }: AlertsPageProps) {
  const [selectedSeverity, setSelectedSeverity] = useState<AlertSeverity | 'all'>('all');
  const { alerts, isLoading, error, dismiss, reload } = useAlertsFeed(
    selectedSeverity,
    service,
  );

  return (
    <AppShell>
      <div className="space-y-6">
        <Card
          tone="banner"
          padding="lg"
          className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"
        >
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary">
              Coordination Alerts Feed
            </h1>
            <p className="mt-1 text-xs font-medium text-ink-muted">
              Real-time triggers when a channel crosses a risk threshold or a new cluster reaches N
              channels
            </p>
          </div>
          <Badge variant="brand" icon="bell">
            {alerts.length} Active Alerts
          </Badge>
        </Card>

        <Card padding="sm" className="flex flex-wrap items-center justify-between gap-4">
          <span className="text-xs font-semibold text-ink-secondary">
            Filter alerts by severity level:
          </span>
          <Tabs
            ariaLabel="Alert severity filter"
            variant="soft"
            items={SEVERITY_TABS}
            value={selectedSeverity}
            onChange={setSelectedSeverity}
          />
        </Card>

        {isLoading ? (
          <div aria-label="Loading alerts feed" className="space-y-3">
            <Skeleton variant="block" className="h-24 w-full" />
            <Skeleton variant="block" className="h-24 w-full" />
          </div>
        ) : error ? (
          <EmptyState
            icon="triangle-exclamation"
            title="Unable to Load Alerts Feed"
            description={error}
            action={
              <Button variant="primary" size="sm" leftIcon="rotate-right" onClick={reload}>
                Retry
              </Button>
            }
          />
        ) : alerts.length === 0 ? (
          <EmptyState
            icon="circle-check"
            title="No Active Alerts"
            description="All alerts in this severity band have been reviewed or dismissed."
          />
        ) : (
          <section aria-label="Latest alerts list" className="space-y-3.5">
            {alerts.map((alert) => (
              <AlertCard key={alert.id} alert={alert} onDismiss={dismiss} />
            ))}
          </section>
        )}
      </div>
    </AppShell>
  );
}

