import { useNavigate } from 'react-router-dom';
import type { RiskiestChannelItemDto, TopClusterItemDto } from '../../../dtos/dashboard.dto';
import { Badge, Card, CardHeader, Icon } from '../../../components/ui';

export interface NeedsAttentionSectionProps {
  topClusters?: readonly TopClusterItemDto[];
  riskiestChannels?: readonly RiskiestChannelItemDto[];
}

export function NeedsAttentionSection({
  topClusters = [],
  riskiestChannels = [],
}: NeedsAttentionSectionProps) {
  const navigate = useNavigate();

  return (
    <section aria-label="Needs attention" className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold tracking-tight text-ink-primary">
          Needs Attention
        </h2>
        <span className="text-xs font-semibold text-ink-muted">
          Active alerts and high-risk signals
        </span>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Left Column: Top Clusters Needing Attention */}
        <Card tone="default" className="flex flex-col justify-between p-5">
          <div>
            <CardHeader
              title="Top Clusters Needing Attention"
              subtitle="Largest multi-channel cascades in the active period"
              action={
                <button
                  type="button"
                  onClick={() => navigate('/clusters')}
                  className="inline-flex items-center gap-1 text-xs font-bold text-brand-700 transition-colors hover:text-brand-800"
                >
                  <span>View all</span>
                  <Icon name="arrow-right" className="text-[10px]" />
                </button>
              }
            />

            <div className="mt-4 space-y-3">
              {topClusters.length === 0 ? (
                <div className="rounded-card border border-brand-100/40 bg-surface-muted/30 py-6 text-center">
                  <p className="text-xs font-medium text-ink-muted">No coordinated clusters detected yet</p>
                </div>
              ) : (
                topClusters.slice(0, 3).map((cluster) => (
                  <div
                    key={cluster.id}
                    onClick={() => navigate(`/clusters/${cluster.id}`)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        navigate(`/clusters/${cluster.id}`);
                      }
                    }}
                    className="group flex cursor-pointer flex-col gap-2 rounded-card border border-brand-100/70 bg-surface-card p-3.5 shadow-xs transition-all hover:border-brand-300 hover:shadow-card"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-xs font-bold text-ink-primary group-hover:text-brand-800">
                        {cluster.headline}
                      </p>
                      <Badge variant="high">
                        HIGH
                      </Badge>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-[11px] text-ink-muted">
                      <span className="truncate font-medium text-brand-700">
                        {cluster.narrativeCategory}
                      </span>
                      <div className="flex items-center gap-3 shrink-0 font-semibold">
                        <span className="flex items-center gap-1">
                          <Icon name="tower-broadcast" className="text-[10px] text-ink-muted" />
                          {cluster.channelsCount} channels
                        </span>
                        <span>•</span>
                        <span>{cluster.timeWindow}</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </Card>

        {/* Right Column: Riskiest Channels */}
        <Card tone="default" className="flex flex-col justify-between p-5">
          <div>
            <CardHeader
              title="Riskiest Channels"
              subtitle="Channels with highest coordination participation"
              action={
                <button
                  type="button"
                  onClick={() => navigate('/channels')}
                  className="inline-flex items-center gap-1 text-xs font-bold text-brand-700 transition-colors hover:text-brand-800"
                >
                  <span>View all</span>
                  <Icon name="arrow-right" className="text-[10px]" />
                </button>
              }
            />

            <div className="mt-4 space-y-2.5">
              {riskiestChannels.length === 0 ? (
                <div className="rounded-card border border-brand-100/40 bg-surface-muted/30 py-6 text-center">
                  <p className="text-xs font-medium text-ink-muted">No monitored channels scored yet</p>
                </div>
              ) : (
                riskiestChannels.slice(0, 5).map((channel) => (
                  <div
                    key={channel.id}
                    onClick={() => navigate(`/channels/${channel.id}`)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        navigate(`/channels/${channel.id}`);
                      }
                    }}
                    className="group flex cursor-pointer items-center justify-between gap-3 rounded-card border border-brand-100/60 bg-surface-card px-3.5 py-2.5 shadow-xs transition-all hover:border-brand-300 hover:shadow-card"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate text-xs font-bold text-ink-primary group-hover:text-brand-800">
                          {channel.title}
                        </p>
                        <span className="truncate text-[10px] font-medium text-ink-muted">
                          {channel.handle}
                        </span>
                      </div>
                      <p className="mt-0.5 truncate text-[11px] font-medium text-ink-secondary">
                        {channel.primaryNarrative}
                      </p>
                    </div>

                    <div className="flex shrink-0 items-center gap-2.5">
                      <Badge
                        variant={channel.score >= 70 ? 'high' : 'medium'}
                      >
                        {channel.score >= 70 ? 'HIGH' : 'MED'} {channel.score}
                      </Badge>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </Card>
      </div>
    </section>
  );
}

