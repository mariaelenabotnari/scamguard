import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { AlertItemDto } from '../../../dtos/alert.dto';
import type { SystemStatusDto } from '../../../dtos/dashboard.dto';
import { Card, CardHeader, Icon } from '../../../components/ui';
import { isMockMode } from '../../../lib/api/http-client';
import { alertService } from '../../../services/alert.service';

export interface SystemStatusWidgetProps {
  systemStatus?: SystemStatusDto;
}

const FALLBACK_MOCK_ALERTS = [
  {
    id: 'alt-01',
    title: 'High coordination detected: 5 channels posted identical message in 8m',
    triggeredAt: '12m ago',
    severity: 'high' as const,
  },
  {
    id: 'alt-02',
    title: 'Channel coordination threshold exceeded for watched channel',
    triggeredAt: '45m ago',
    severity: 'medium' as const,
  },
];

export function SystemStatusWidget({
  systemStatus,
}: SystemStatusWidgetProps) {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<readonly AlertItemDto[]>([]);

  useEffect(() => {
    let isMounted = true;
    alertService
      .getAlerts()
      .then((data) => {
        if (isMounted) {
          setAlerts(data);
        }
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, []);

  const visibleAlerts = isMockMode() && alerts.length === 0 ? FALLBACK_MOCK_ALERTS : alerts.slice(0, 3);

  return (
    <Card tone="default" className="flex flex-col justify-between p-5">
      <div>
        <CardHeader
          title="Latest Alerts & System Status"
          subtitle="Real-time monitoring health and recent trigger events"
          action={
            <button
              type="button"
              onClick={() => navigate('/alerts')}
              className="inline-flex items-center gap-1 text-xs font-bold text-brand-700 transition-colors hover:text-brand-800"
            >
              <span>All alerts</span>
              <Icon name="arrow-right" className="text-[10px]" />
            </button>
          }
        />

        {/* Alerts Feed */}
        <div className="mt-4 space-y-2.5">
          {visibleAlerts.length === 0 ? (
            <div className="rounded-card border border-brand-100/40 bg-surface-muted/30 py-5 text-center">
              <p className="text-xs font-medium text-ink-muted">No active alerts • All channels nominal</p>
            </div>
          ) : (
            visibleAlerts.map((alert) => (
              <div
                key={alert.id}
                onClick={() => navigate('/alerts')}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    navigate('/alerts');
                  }
                }}
                className="flex cursor-pointer items-start gap-2.5 rounded-card border border-brand-100/60 bg-surface-card p-3 shadow-xs transition-all hover:border-brand-300 hover:shadow-card"
              >
                <span
                  className={`mt-1 h-2 w-2 shrink-0 rounded-full ${
                    alert.severity === 'high'
                      ? 'bg-status-dangerText'
                      : alert.severity === 'medium'
                      ? 'bg-status-warningText'
                      : 'bg-brand-500'
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <p className="line-clamp-2 text-xs font-semibold text-ink-primary">
                    {alert.title}
                  </p>
                  <span className="mt-1 block text-[10px] font-medium text-ink-muted">
                    {alert.triggeredAt?.includes('T')
                      ? new Date(alert.triggeredAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                      : alert.triggeredAt || 'Recent'}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* System Health Indicators */}
        <div className="mt-4 rounded-card border border-brand-100/70 bg-surface-muted/50 p-3.5">
          <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-3">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">
                Ingestion
              </span>
              <div className="mt-1 flex items-center gap-1.5 font-bold text-status-successText">
                <span className="h-2 w-2 rounded-full bg-status-successText" />
                <span>Operational</span>
              </div>
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">
                Pipeline
              </span>
              <p className="mt-1 font-bold text-ink-primary">
                {systemStatus?.nextRunLabel ? `Active (${systemStatus.nextRunLabel})` : 'Active'}
              </p>
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">
                Last Run
              </span>
              <p className="mt-1 font-bold text-ink-secondary">
                {systemStatus?.lastCollectionLabel || 'Active'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

