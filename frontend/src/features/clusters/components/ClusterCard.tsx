import { Link } from 'react-router-dom';
import { Badge, Button, Card, Icon } from '../../../components/ui';
import type { ClusterMatchType, ClusterSummaryDto } from '../../../dtos/cluster.dto';
import { ChannelAvatarStack } from './ChannelAvatarStack';

export interface ClusterCardProps {
  cluster: ClusterSummaryDto;
}

const MATCH_TYPE_LABEL: Record<ClusterMatchType, string> = {
  exact: 'Exact Hash Match',
  minhash: 'MinHash LSH Near-Duplicate',
  semantic: 'Multilingual Semantic Match',
};

export function ClusterCard({ cluster }: ClusterCardProps) {
  return (
    <Card className="space-y-4 transition-shadow hover:shadow-shell/40">
      {/* Top Row: Narrative Category Tag, Similarity & Parameter Version */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="brand" icon="layer-group">
            {cluster.narrativeCategory}
          </Badge>
          <Badge variant="high" icon="circle-nodes">
            {Math.round(cluster.averageSimilarity * 100)}% Similarity •{' '}
            {MATCH_TYPE_LABEL[cluster.matchType]}
          </Badge>
        </div>

        <span className="text-[11px] font-semibold text-ink-muted">
          Narrative Confidence {Math.round(cluster.narrativeConfidence * 100)}% • Param{' '}
          {cluster.parameterVersion}
        </span>
      </div>

      {/* Coordination Headline & Snippet */}
      <div className="space-y-1.5">
        <h2 className="text-base font-extrabold text-ink-primary">
          {cluster.headlineSummary}
        </h2>
        <p className="rounded-badge bg-surface-muted/80 p-3.5 text-xs leading-relaxed text-ink-secondary">
          “{cluster.representativeSnippet}”
        </p>
      </div>

      {/* Bottom Row: Channel Avatars, First/Last Timestamps, and Compare Action */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-t border-brand-100 pt-3.5">
        <ChannelAvatarStack participants={cluster.participants} />

        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2 text-xs font-medium text-ink-muted">
            <Icon name="clock" className="text-brand-700" />
            <span>
              First: <strong className="text-ink-primary">{cluster.firstPostedAt}</strong>
            </span>
            <span>→</span>
            <span>
              Last: <strong className="text-ink-primary">{cluster.lastPostedAt}</strong>
            </span>
          </div>

          <Link to={`/clusters/${cluster.id}`}>
            <Button variant="primary" size="sm" rightIcon="chevron-right">
              Compare Messages
            </Button>
          </Link>
        </div>
      </div>
    </Card>
  );
}

