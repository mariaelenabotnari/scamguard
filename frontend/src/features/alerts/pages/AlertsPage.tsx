import { useState } from 'react';
import { AppShell } from '../../../components/layout';
import {
  Button,
  Card,
  CardHeader,
  EmptyState,
  Icon,
  Input,
  Skeleton,
  Tabs,
} from '../../../components/ui';
import type { AlertSeverity } from '../../../dtos/alert.dto';
import {
  alertService,
  type IAlertService,
} from '../../../services/alert.service';
import { ExportModal } from '../../export/components/ExportModal';
import { AlertCard } from '../components/AlertCard';
import { useAlertsFeed } from '../hooks/useAlertsFeed';

export interface AlertsPageProps {
  service?: IAlertService;
}

type MainTab = 'feed' | 'settings';

const SEVERITY_TABS: readonly { value: AlertSeverity | 'all'; label: string }[] = [
  { value: 'all', label: 'All Alerts' },
  { value: 'high', label: 'High Priority' },
  { value: 'medium', label: 'Medium Priority' },
  { value: 'low', label: 'Low Priority' },
];

export function AlertsPage({ service = alertService }: AlertsPageProps) {
  const [activeMainTab, setActiveMainTab] = useState<MainTab>('feed');
  const [selectedSeverity, setSelectedSeverity] = useState<AlertSeverity | 'all'>('all');

  // Notification settings state
  const [emailAlerts, setEmailAlerts] = useState<boolean>(true);
  const [recipientEmail, setRecipientEmail] = useState<string>('elena.botnari@scamguard.md');
  const [riskThreshold, setRiskThreshold] = useState<number>(70);
  const [minClusterChannels, setMinClusterChannels] = useState<number>(3);
  const [settingsSaved, setSettingsSaved] = useState<boolean>(false);

  const { alerts, isLoading, error, dismiss, reload } = useAlertsFeed(
    selectedSeverity,
    service,
  );

  const handleSaveSettings = (e: React.FormEvent) => {
    e.preventDefault();
    setSettingsSaved(true);
    setTimeout(() => setSettingsSaved(false), 3000);
  };

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary">
              Alerts
            </h1>
            <p className="mt-0.5 text-xs font-medium text-ink-muted">
              Real-time notifications for coordinated message spikes and channel risk changes.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <ExportModal defaultEntity="clusters" />
          </div>
        </div>

        {/* Main View Tabs */}
        <div className="flex items-center gap-2 border-b border-brand-100 pb-2">
          <button
            type="button"
            onClick={() => setActiveMainTab('feed')}
            className={`rounded-badge px-4 py-2 text-xs font-bold transition-all ${
              activeMainTab === 'feed'
                ? 'bg-brand-700 text-white shadow-xs'
                : 'bg-surface-card text-ink-muted hover:text-ink-primary'
            }`}
          >
            Alerts Feed ({alerts.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveMainTab('settings')}
            className={`rounded-badge px-4 py-2 text-xs font-bold transition-all ${
              activeMainTab === 'settings'
                ? 'bg-brand-700 text-white shadow-xs'
                : 'bg-surface-card text-ink-muted hover:text-ink-primary'
            }`}
          >
            Notification Settings
          </button>
        </div>

        {activeMainTab === 'feed' ? (
          <>
            {/* Filter Bar */}
            <Card padding="sm" className="flex flex-wrap items-center justify-between gap-4">
              <span className="text-xs font-semibold text-ink-secondary">
                Filter by priority level:
              </span>
              <Tabs
                ariaLabel="Alert severity filter"
                variant="soft"
                items={SEVERITY_TABS}
                value={selectedSeverity}
                onChange={setSelectedSeverity}
              />
            </Card>

            {/* Alerts List */}
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
                description="All alerts in this priority band have been reviewed or dismissed."
              />
            ) : (
              <section aria-label="Latest alerts list" className="space-y-3.5">
                {alerts.map((alert) => (
                  <AlertCard key={alert.id} alert={alert} onDismiss={dismiss} />
                ))}
              </section>
            )}
          </>
        ) : (
          /* Notification Settings Tab */
          <Card className="p-6">
            <form onSubmit={handleSaveSettings} className="space-y-5 max-w-xl">
              <CardHeader
                title="Alert Notification Rules"
                subtitle="Configure threshold alerts for newsroom and researcher teams"
              />

              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-badge border border-brand-100 bg-surface-muted/60 p-4">
                  <div>
                    <p className="text-xs font-bold text-ink-primary">Email Notifications</p>
                    <p className="text-[11px] text-ink-muted">Send digest alerts when high-risk cascades trigger</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={emailAlerts}
                    onChange={(e) => setEmailAlerts(e.target.checked)}
                    className="h-4 w-4 cursor-pointer rounded border-brand-300 text-brand-700 focus:ring-brand-500"
                  />
                </div>

                {emailAlerts ? (
                  <Input
                    label="Notification Email Address"
                    type="email"
                    value={recipientEmail}
                    onChange={(e) => setRecipientEmail(e.target.value)}
                    hint="Verified newsroom dispatch address"
                  />
                ) : null}

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <Input
                    label="Risk Threshold (0–100)"
                    type="number"
                    value={String(riskThreshold)}
                    onChange={(e) => setRiskThreshold(Number(e.target.value))}
                    hint="Alert triggers when channel score exceeds this level"
                  />
                  <Input
                    label="Min Cluster Channels"
                    type="number"
                    value={String(minClusterChannels)}
                    onChange={(e) => setMinClusterChannels(Number(e.target.value))}
                    hint="Alert triggers when identical text reaches N channels"
                  />
                </div>
              </div>

              {settingsSaved ? (
                <div className="rounded-xl bg-status-successBg p-3 text-xs font-bold text-status-successText">
                  <Icon name="circle-check" className="mr-1.5" />
                  Alert threshold preferences saved successfully.
                </div>
              ) : null}

              <div className="flex justify-end pt-2">
                <Button type="submit" variant="primary" leftIcon="check">
                  Save Preferences
                </Button>
              </div>
            </form>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
