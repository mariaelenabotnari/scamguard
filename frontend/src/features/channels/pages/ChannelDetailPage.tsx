import { Link, useParams } from 'react-router-dom';
import { AppShell } from '../../../components/layout';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Skeleton,
} from '../../../components/ui';
import type { IChannelService } from '../../../services/channel.service';
import { Sparkline } from '../../ranking/components/Sparkline';
import { useChannelDetail } from '../hooks/useChannelDetail';

export interface ChannelDetailPageProps {
  service?: IChannelService;
}

export function ChannelDetailPage({ service }: ChannelDetailPageProps) {
  const { channelId = 'ch-moldova-pulse' } = useParams<{ channelId: string }>();
  const { channel, isLoading, error, reload } = useChannelDetail(channelId, service);

  return (
    <AppShell>
      <div className="space-y-6">
        {isLoading ? (
          <div aria-label="Loading channel profile" className="space-y-4">
            <Skeleton variant="block" className="h-28 w-full" />
            <Skeleton variant="block" className="h-48 w-full" />
            <Skeleton variant="block" className="h-48 w-full" />
          </div>
        ) : error || !channel ? (
          <EmptyState
            icon="triangle-exclamation"
            title="Unable to Load Channel Profile"
            description={error ?? 'Channel not found.'}
            action={
              <Button variant="primary" size="sm" leftIcon="rotate-right" onClick={reload}>
                Retry
              </Button>
            }
          />
        ) : (
          <>
            {/* Channel Header & Score Summary */}
            <Card
              tone="banner"
              padding="lg"
              className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"
            >
              <div>
                <div className="flex flex-wrap items-center gap-2.5">
                  <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary">
                    {channel.handle}
                  </h1>
                  <Badge variant={channel.riskBand} icon="triangle-exclamation">
                    {channel.riskBand.toUpperCase()} RISK • {channel.score}/100
                  </Badge>
                  <Badge variant="neutral">{channel.language}</Badge>
                </div>
                <p className="mt-1 text-xs font-medium text-ink-muted">
                  {channel.title} • {channel.subscribersCount.toLocaleString()} subscribers •
                  Monitored since {channel.addedAt}
                </p>
              </div>

              <div className="flex items-center gap-3 rounded-badge bg-surface-card px-4 py-2.5 shadow-card">
                <div>
                  <p className="text-[10px] font-semibold uppercase text-ink-muted">
                    7d Score Trajectory
                  </p>
                  <Sparkline
                    values={channel.scoreHistory.map((p) => p.score)}
                    riskBand={channel.riskBand}
                    label={`${channel.handle} 7-day score history`}
                  />
                </div>
              </div>
            </Card>

            {/* Why Was This Channel Flagged? (Explanation Block - FR-07, NFR-13) */}
            <Card data-testid="channel-explanation-block" className="space-y-4">
              <CardHeader
                title="Why Was This Channel Flagged? (Coordination Explanation)"
                subtitle={`Deterministic score breakdown • Parameter Version ${channel.explanation.parameterVersion}`}
                action={
                  <Badge variant="brand" icon="layer-group">
                    {channel.explanation.dominantNarrativeCategory}
                  </Badge>
                }
              />

              <p className="rounded-badge bg-surface-banner/80 p-4 text-xs font-semibold leading-relaxed text-ink-primary">
                {channel.explanation.summary}
              </p>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-badge bg-surface-muted p-3.5">
                  <p className="text-[11px] font-medium text-ink-muted">Cluster Share</p>
                  <p className="mt-1 text-lg font-extrabold text-ink-primary">
                    +{channel.explanation.breakdown.clusterShareScore} pts
                  </p>
                </div>
                <div className="rounded-badge bg-surface-muted p-3.5">
                  <p className="text-[11px] font-medium text-ink-muted">Copy Delay Speed</p>
                  <p className="mt-1 text-lg font-extrabold text-ink-primary">
                    +{channel.explanation.breakdown.copyDelayScore} pts
                  </p>
                </div>
                <div className="rounded-badge bg-surface-muted p-3.5">
                  <p className="text-[11px] font-medium text-ink-muted">Pair Repetition</p>
                  <p className="mt-1 text-lg font-extrabold text-ink-primary">
                    +{channel.explanation.breakdown.pairRepetitionScore} pts
                  </p>
                </div>
                <div className="rounded-badge bg-surface-muted p-3.5">
                  <p className="text-[11px] font-medium text-ink-muted">Narrative Weight</p>
                  <p className="mt-1 text-lg font-extrabold text-ink-primary">
                    +{channel.explanation.breakdown.narrativeWeightScore} pts
                  </p>
                </div>
              </div>

              <p className="text-xs text-ink-secondary">
                <strong className="text-ink-primary">Primary Score Driver:</strong>{' '}
                {channel.explanation.breakdown.dominantFactor}
              </p>
            </Card>

            {/* Two-Column Grid: Co-Moving Channels & Joined Clusters */}
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <Card>
                <CardHeader
                  title="Channels It Moves With (Pair Repetition)"
                  subtitle="Channels posting synchronized messages in the same clusters"
                />
                <div className="space-y-3">
                  {channel.coMovingChannels.map((peer) => (
                    <div
                      key={peer.channelId}
                      className="flex items-center justify-between rounded-badge bg-surface-muted p-3.5"
                    >
                      <div>
                        <Link
                          to={`/channels/${peer.channelId}`}
                          className="text-sm font-bold text-ink-primary hover:text-brand-700 hover:underline"
                        >
                          {peer.handle}
                        </Link>
                        <p className="text-xs text-ink-muted">
                          {peer.sharedClustersCount} shared clusters • median lag{' '}
                          {peer.medianTimeDiffSeconds}s
                        </p>
                      </div>
                      <Badge variant="brand">
                        {Math.round(peer.averageSimilarity * 100)}% avg match
                      </Badge>
                    </div>
                  ))}
                </div>
              </Card>

              <Card>
                <CardHeader
                  title="Participating Clusters"
                  subtitle="Recent multi-channel message clusters joined by this channel"
                />
                <div className="space-y-3">
                  {channel.joinedClusters.map((cl) => (
                    <div
                      key={cl.clusterId}
                      className="flex flex-col justify-between gap-2 rounded-badge bg-surface-muted p-3.5 sm:flex-row sm:items-center"
                    >
                      <div>
                        <p className="text-xs font-bold text-ink-primary">
                          {cl.headlineSummary}
                        </p>
                        <p className="mt-0.5 text-[11px] text-ink-muted">
                          {cl.narrativeCategory} • Posted {cl.postedAt} (+{cl.delaySeconds}s)
                        </p>
                      </div>
                      <Link to={`/clusters/${cl.clusterId}`}>
                        <Button variant="secondary" size="sm" rightIcon="chevron-right">
                          Compare
                        </Button>
                      </Link>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
