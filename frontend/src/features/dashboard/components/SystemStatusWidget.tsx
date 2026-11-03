import { useNavigate } from 'react-router-dom';
import type { SystemStatusDto } from '../../../dtos/dashboard.dto';
import { Card, CardHeader, Icon } from '../../../components/ui';

export interface SystemStatusWidgetProps {
  systemStatus?: SystemStatusDto;
}

const RECENT_ALERTS = [
  {
    id: 'alt-01',
    message: 'High coordination detected: 5 channels posted identical gas price message in 8m',
    time: '12m ago',
    risk: 'high',
  },
  {
    id: 'alt-02',
    message: 'New channel added to high-risk ranking: @gagauzia_voice_md',
    time: '45m ago',
    risk: 'medium',
  },
  {
    id: 'alt-03',
    message: 'Telegram ingestion recovered: 124 missed messages processed',
    time: '2h ago',
    risk: 'info',
  },
];

export function SystemStatusWidget({
  systemStatus,
}: SystemStatusWidgetProps) {
  const navigate = useNavigate();

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

        {/* Recent Alerts Feed */}
        <div className="mt-4 space-y-2.5">
          {RECENT_ALERTS.map((alert) => (
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
                  alert.risk === 'high'
                    ? 'bg-status-dangerText'
                    : alert.risk === 'medium'
                    ? 'bg-status-warningText'
                    : 'bg-brand-500'
                }`}
              />
              <div className="min-w-0 flex-1">
                <p className="line-clamp-2 text-xs font-semibold text-ink-primary">
                  {alert.message}
                </p>
                <span className="mt-1 block text-[10px] font-medium text-ink-muted">
                  {alert.time}
                </span>
              </div>
            </div>
          ))}
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
                {systemStatus?.lastCollectionLabel || '2m ago'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

