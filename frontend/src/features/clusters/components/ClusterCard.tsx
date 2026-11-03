import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Badge, Button, Card, Icon } from '../../../components/ui';
import type { ClusterMatchType, ClusterSummaryDto } from '../../../dtos/cluster.dto';
import { ChannelAvatarStack } from './ChannelAvatarStack';

export interface ClusterCardProps {
  cluster: ClusterSummaryDto;
}

const PLAIN_MATCH_METHOD: Record<ClusterMatchType, string> = {
  exact: 'Exact copy',
  minhash: 'Almost the same text',
  semantic: 'Same meaning, different words',
};

export function ClusterCard({ cluster }: ClusterCardProps) {
  const navigate = useNavigate();
  const [showDetails, setShowDetails] = useState<boolean>(false);

  return (
    <Card className="space-y-4 transition-all hover:shadow-shell/40">
      {/* Top Row: Narrative Chip, Channel Count & Time Span, and Details Button */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="brand">
            {cluster.narrativeCategory}
          </Badge>
          <span className="text-xs font-semibold text-brand-800">
            {cluster.participants.length} channels • {cluster.spanMinutes}m spread
          </span>
        </div>

        <div className="relative">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setShowDetails((prev) => !prev);
            }}
            aria-label="View cluster detection details"
            className="inline-flex items-center gap-1 text-xs font-semibold text-ink-muted hover:text-brand-700 focus:outline-none"
          >
            <Icon name="circle-info" className="text-xs" />
            <span>Details</span>
          </button>

          {/* Details Tooltip / Popover */}
          {showDetails ? (
            <div
              role="tooltip"
              className="absolute right-0 top-6 z-20 w-64 rounded-card border border-brand-200 bg-surface-card p-3 shadow-shell text-xs"
            >
              <div className="flex items-center justify-between border-b border-brand-100 pb-1.5 font-bold text-ink-primary">
                <span>Detection Details</span>
                <button
                  type="button"
                  onClick={() => setShowDetails(false)}
                  className="text-ink-muted hover:text-ink-primary"
                >
                  <Icon name="xmark" />
                </button>
              </div>
              <div className="mt-2 space-y-1.5 text-ink-secondary">
                <p>
                  <strong>Detection Method:</strong> {PLAIN_MATCH_METHOD[cluster.matchType]}
                </p>
                <p>
                  <strong>Text Match:</strong> {Math.round(cluster.averageSimilarity * 100)}% similarity
                </p>
                <p>
                  <strong>Narrative Confidence:</strong> {Math.round(cluster.narrativeConfidence * 100)}%
                </p>
                <p className="text-[10px] text-ink-muted pt-1 border-t border-brand-100">
                  Settings used: {cluster.parameterVersion}
                </p>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {/* Coordination Headline & 2-Line Representative Message Quote */}
      <div
        onClick={() => navigate(`/clusters/${cluster.id}`)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            navigate(`/clusters/${cluster.id}`);
          }
        }}
        className="cursor-pointer space-y-1.5 group"
      >
        <h2 className="text-base font-extrabold text-ink-primary group-hover:text-brand-700">
          {cluster.headlineSummary}
        </h2>
        <p className="line-clamp-2 rounded-badge bg-surface-muted/80 p-3.5 text-xs leading-relaxed text-ink-secondary">
          “{cluster.representativeSnippet}”
        </p>
      </div>

      {/* Bottom Row: Channel Avatars, Time Window, and Inspect Action */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-t border-brand-100 pt-3.5">
        <ChannelAvatarStack participants={cluster.participants} />

        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-1.5 text-xs font-medium text-ink-muted">
            <Icon name="clock" className="text-brand-700" />
            <span>{cluster.firstPostedAt}</span>
            <span>→</span>
            <span>{cluster.lastPostedAt}</span>
            <span>({cluster.spanMinutes}m)</span>
          </div>

          <Button
            variant="primary"
            size="sm"
            rightIcon="chevron-right"
            onClick={() => navigate(`/clusters/${cluster.id}`)}
          >
            Compare Messages
          </Button>
        </div>
      </div>
    </Card>
  );
}
