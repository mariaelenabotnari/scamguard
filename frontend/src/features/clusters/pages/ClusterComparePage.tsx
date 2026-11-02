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
            err instanceof Error ? err.message : 'Failed to load cluster comparison.';
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
          <div aria-label="Loading cluster comparison" className="space-y-4">
            <Skeleton variant="block" className="h-28 w-full" />
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <Skeleton variant="block" className="h-56 w-full" />
              <Skeleton variant="block" className="h-56 w-full" />
            </div>
          </div>
        ) : error || !detail ? (
          <EmptyState
            icon="triangle-exclamation"
            title="Unable to Load Cluster Comparison"
            description={error ?? 'Cluster not found.'}
          />
        ) : (
          <>
            {/* Cluster Comparison Header */}
            <Card
              tone="banner"
              padding="lg"
              className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"
            >
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="brand" icon="layer-group">
                    {detail.summary.narrativeCategory}
                  </Badge>
                  <Badge variant="high">
                    {Math.round(detail.summary.averageSimilarity * 100)}% Avg Similarity
                  </Badge>
                </div>
                <h1 className="mt-2 text-2xl font-extrabold tracking-tight text-ink-primary">
                  {detail.summary.headlineSummary}
                </h1>
                <p className="mt-1 text-xs font-medium text-ink-muted">
                  Window: {detail.summary.firstPostedAt} → {detail.summary.lastPostedAt} •
                  Parameter Version {detail.summary.parameterVersion}
                </p>
              </div>
              <Link to="/clusters">
                <Button variant="secondary" size="sm" leftIcon="chevron-left">
                  Back to Clusters
                </Button>
              </Link>
            </Card>

            {/* Side-by-Side Message Cards */}
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
                            +{post.delaySeconds}s • {Math.round(post.similarityToAnchor * 100)}%
                            match
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
                          Per data minimisation policy (NFR-11), raw text was purged when the
                          source post was removed. Retaining normalised text and hash only:
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

                  {/* Footer Metadata: Hash & Original Post Link */}
                  <div className="flex flex-wrap items-center justify-between gap-2 border-t border-brand-100 pt-3 text-[11px] text-ink-muted">
                    <span className="font-mono">{post.textHash}</span>
                    {post.isDeletedAtSource || !post.originalUrl ? (
                      <span className="font-semibold text-status-dangerText">
                        Original link unavailable
                      </span>
                    ) : (
                      <a
                        href={post.originalUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 font-bold text-brand-700 hover:underline"
                      >
                        <span>View Original Telegram Post</span>
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

