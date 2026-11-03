import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AppShell } from '../../../components/layout';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Icon,
  Skeleton,
} from '../../../components/ui';
import type { ClusterDetailDto } from '../../../dtos/cluster.dto';
import {
  clusterService,
  type IClusterService,
} from '../../../services/cluster.service';
import { ExportModal } from '../../export/components/ExportModal';

export interface ClusterComparePageProps {
  service?: IClusterService;
}

export function ClusterComparePage({
  service = clusterService,
}: ClusterComparePageProps) {
  const { clusterId = 'cl-energy-winter-01' } = useParams<{ clusterId: string }>();
  const [detail, setDetail] = useState<ClusterDetailDto | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    service
      .getClusterDetail(clusterId)
      .then((result) => {
        if (isMounted) {
          setDetail(result);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const message =
            err instanceof Error ? err.message : 'Failed to load cluster detail.';
          setError(message);
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [clusterId, service]);

  return (
    <AppShell>
      <div className="space-y-6">
        {isLoading ? (
          <div aria-label="Loading cluster detail" className="space-y-4">
            <Skeleton variant="block" className="h-28 w-full" />
            <Skeleton variant="block" className="h-44 w-full" />
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <Skeleton variant="block" className="h-56 w-full" />
              <Skeleton variant="block" className="h-56 w-full" />
            </div>
          </div>
        ) : error || !detail ? (
          <EmptyState
            icon="triangle-exclamation"
            title="Unable to Load Cluster Detail"
            description={error ?? 'Cluster not found.'}
          />
        ) : (
          <>
            {/* Cluster Header */}
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="brand">
                    {detail.summary.narrativeCategory}
                  </Badge>
                  <span className="text-xs font-semibold text-brand-800">
                    {detail.posts.length} channels involved • {detail.summary.spanMinutes}m spread
                  </span>
                </div>
                <h1 className="mt-1.5 text-2xl font-extrabold tracking-tight text-ink-primary">
                  {detail.summary.headlineSummary}
                </h1>
                <p className="mt-0.5 text-xs font-medium text-ink-muted">
                  First posted {detail.summary.firstPostedAt} → Last copy {detail.summary.lastPostedAt}
                </p>
              </div>

              <div className="flex items-center gap-2.5">
                <ExportModal defaultEntity="clusters" />
                <Link to="/clusters">
                  <Button variant="secondary" size="sm" leftIcon="chevron-left">
                    Back to Clusters
                  </Button>
                </Link>
              </div>
            </div>

            {/* Spread Timeline: Shows who posted first and progression */}
            <Card className="space-y-4 p-5">
              <CardHeader
                title="Spread Timeline"
                subtitle="Chronological sequence of channels posting this message"
              />

              <div className="relative mt-2 overflow-x-auto pb-4">
                <div className="min-w-[640px] pt-6 pb-2">
                  {/* Timeline Bar Line */}
                  <div className="relative flex items-center justify-between">
                    <div className="absolute left-6 right-6 top-5 h-1 bg-brand-200/70" />

                    {detail.posts.map((post, idx) => (
                      <div
                        key={post.id}
                        className="relative z-10 flex flex-col items-center text-center group"
                      >
                        {/* Delay Pill */}
                        <span className="mb-2 text-[10px] font-bold text-ink-secondary">
                          {idx === 0 ? 'First Source' : `+${post.delaySeconds}s`}
                        </span>

                        {/* Node Bubble */}
                        <div
                          className={`flex h-10 w-10 items-center justify-center rounded-full border-2 shadow-xs transition-all ${
                            idx === 0
                              ? 'border-brand-700 bg-brand-800 text-white font-bold'
                              : 'border-brand-300 bg-surface-card text-brand-700 font-semibold hover:border-brand-500'
                          }`}
                        >
                          {post.handle.slice(1, 3).toUpperCase()}
                        </div>

                        {/* Channel Label & Time */}
                        <div className="mt-2 space-y-0.5 max-w-[120px]">
                          <Link
                            to={`/channels/${post.channelId}`}
                            className="text-xs font-bold text-ink-primary hover:text-brand-700 block truncate"
                          >
                            {post.handle}
                          </Link>
                          <span className="text-[10px] text-ink-muted block truncate">
                            {post.postedAt.split(' ')[1] || post.postedAt}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>

            {/* Side-by-Side Message Comparison */}
            <section
              aria-label="Side-by-side message comparison"
              className="grid grid-cols-1 gap-6 lg:grid-cols-2"
            >
              {detail.posts.map((post, index) => (
                <Card key={post.id} className="flex flex-col justify-between space-y-4">
                  <div className="space-y-3">
                    <CardHeader
                      title={
                        <Link
                          to={`/channels/${post.channelId}`}
                          className="hover:text-brand-700 hover:underline"
                        >
                          {post.handle}
                        </Link>
                      }
                      subtitle={`${post.channelTitle} • Posted ${post.postedAt}`}
                      action={
                        index === 0 ? (
                          <Badge variant="brand">First Source (0s)</Badge>
                        ) : (
                          <Badge variant="medium">
                            +{post.delaySeconds}s • {Math.round(post.similarityToAnchor * 100)}% match
                          </Badge>
                        )
                      }
                    />

                    {post.isDeletedAtSource ? (
                      <div
                        data-testid={`deleted-post-${post.id}`}
                        className="space-y-2 rounded-badge border border-status-warningText/30 bg-status-warningBg/70 p-4"
                      >
                        <div className="flex items-center gap-2 text-xs font-bold text-status-warningText">
                          <Icon name="triangle-exclamation" />
                          <span>Original no longer available at source (Deleted Post)</span>
                        </div>
                        <p className="text-[11px] text-ink-secondary">
                          Raw message text was removed from source Telegram channel. Storing normalized evidence snippet:
                        </p>
                        <p className="rounded bg-surface-card p-2.5 font-mono text-xs text-ink-primary">
                          {post.normalizedText}
                        </p>
                      </div>
                    ) : (
                      <div className="rounded-badge bg-surface-muted p-4 text-xs leading-relaxed text-ink-primary">
                        {post.diffTokens.length > 0 ? (
                          <p>
                            {post.diffTokens.map((token, tokenIdx) =>
                              token.isChanged ? (
                                <mark
                                  key={tokenIdx}
                                  className="rounded bg-status-warningBg px-1 py-0.5 font-bold text-status-warningText"
                                >
                                  {token.text}
                                </mark>
                              ) : (
                                <span key={tokenIdx}>{token.text}</span>
                              ),
                            )}
                          </p>
                        ) : (
                          <p>{post.rawText}</p>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Original Post Action */}
                  <div className="flex flex-wrap items-center justify-between gap-2 border-t border-brand-100 pt-3 text-[11px] text-ink-muted">
                    <span className="font-mono text-[10px]">{post.textHash}</span>
                    {post.isDeletedAtSource || !post.originalUrl ? (
                      <span className="font-semibold text-status-dangerText">
                        Source post deleted
                      </span>
                    ) : (
                      <a
                        href={post.originalUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 font-bold text-brand-700 hover:underline"
                      >
                        <span>View Original on Telegram</span>
                        <Icon name="arrow-right" className="text-[10px]" />
                      </a>
                    )}
                  </div>
                </Card>
              ))}
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}
