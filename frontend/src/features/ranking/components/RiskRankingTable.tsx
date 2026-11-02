import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Badge,
  Button,
  EmptyState,
  Icon,
  Modal,
  Table,
  type TableColumn,
} from '../../../components/ui';
import type { RankedChannelDto } from '../../../dtos/ranking.dto';
import { Sparkline } from './Sparkline';

export interface RiskRankingTableProps {
  channels: readonly RankedChannelDto[];
}

export function RiskRankingTable({ channels }: RiskRankingTableProps) {
  const [explainedChannel, setExplainedChannel] = useState<RankedChannelDto | null>(null);

  if (channels.length === 0) {
    return (
      <EmptyState
        icon="satellite-dish"
        title="No Ranked Channels Match Filter"
        description="Try clearing the search query or switching the risk band filter."
      />
    );
  }

  const columns: readonly TableColumn<RankedChannelDto>[] = [
    {
      key: 'rank',
      header: '#',
      render: (_row, index) => (
        <span className="text-xs font-bold text-ink-muted">{index + 1}</span>
      ),
    },
    {
      key: 'channel',
      header: 'Channel',
      render: (row) => (
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <Link
              to={`/channels/${row.id}`}
              className="font-bold text-ink-primary hover:text-brand-700 hover:underline"
            >
              {row.handle}
            </Link>
            <span className="rounded bg-surface-muted px-1.5 py-0.5 text-[10px] font-bold text-ink-muted">
              {row.language}
            </span>
          </div>
          <p className="text-xs text-ink-muted">
            {row.title} • {row.subscribersCount.toLocaleString()} subscribers
          </p>
        </div>
      ),
    },
    {
      key: 'narrative',
      header: 'Dominant Narrative & Clusters',
      render: (row) => (
        <div className="space-y-1">
          <Badge variant="brand" icon="layer-group">
            {row.primaryNarrative}
          </Badge>
          <p className="text-[11px] font-medium text-ink-muted">
            {row.clustersJoinedCount} coordinated clusters • median delay{' '}
            {Math.round(row.explanation.medianCopyDelaySeconds / 60)}m
          </p>
        </div>
      ),
    },
    {
      key: 'sparkline',
      header: '7d Trend',
      render: (row) => (
        <Sparkline
          values={row.sparkline}
          riskBand={row.riskBand}
          label={`${row.handle} 7-day score trend`}
        />
      ),
    },
    {
      key: 'score',
      header: 'Coordination Risk Score',
      render: (row) => (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Badge
              variant={row.riskBand}
              icon={
                row.riskBand === 'high'
                  ? 'triangle-exclamation'
                  : row.riskBand === 'medium'
                    ? 'clock'
                    : 'circle-check'
              }
            >
              {row.riskBand.toUpperCase()} • {row.score}/100
            </Badge>
            <button
              type="button"
              onClick={() => setExplainedChannel(row)}
              aria-label={`Explain score for ${row.handle}`}
              className="inline-flex items-center gap-1 rounded-lg bg-surface-muted px-2 py-1 text-[11px] font-semibold text-brand-700 transition-colors hover:bg-brand-100"
            >
              <Icon name="circle-info" className="text-[10px]" />
              <span>Why?</span>
            </button>
          </div>
          <p className="max-w-xs text-[11px] text-ink-muted">
            {row.explanation.summary}
          </p>
        </div>
      ),
    },
    {
      key: 'actions',
      header: 'Channel Page',
      align: 'right',
      render: (row) => (
        <Link to={`/channels/${row.id}`}>
          <Button variant="secondary" size="sm" rightIcon="chevron-right">
            Inspect
          </Button>
        </Link>
      ),
    },
  ];

  return (
    <>
      <Table
        columns={columns}
        data={channels}
        rowKey={(row) => row.id}
      />

      {explainedChannel ? (
        <Modal
          isOpen={true}
          onClose={() => setExplainedChannel(null)}
          title={`Score Explanation: ${explainedChannel.handle}`}
          subtitle={`Score ${explainedChannel.score}/100 (${explainedChannel.riskBand.toUpperCase()}) • Parameter Version ${explainedChannel.explanation.parameterVersion}`}
          footer={
            <>
              <Button variant="ghost" onClick={() => setExplainedChannel(null)}>
                Close
              </Button>
              <Link to={`/channels/${explainedChannel.id}`}>
                <Button variant="primary" rightIcon="arrow-right">
                  Open Channel Profile
                </Button>
              </Link>
            </>
          }
        >
          <div className="space-y-4">
            <p className="rounded-badge bg-surface-banner p-3 text-xs font-medium text-ink-primary">
              {explainedChannel.explanation.summary}
            </p>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-badge bg-surface-muted p-3">
                <p className="text-[11px] text-ink-muted">Cluster Share Component</p>
                <p className="mt-0.5 text-base font-extrabold text-ink-primary">
                  +{explainedChannel.explanation.breakdown.clusterShareScore} pts
                </p>
              </div>
              <div className="rounded-badge bg-surface-muted p-3">
                <p className="text-[11px] text-ink-muted">Copy Delay Speed</p>
                <p className="mt-0.5 text-base font-extrabold text-ink-primary">
                  +{explainedChannel.explanation.breakdown.copyDelayScore} pts
                </p>
              </div>
              <div className="rounded-badge bg-surface-muted p-3">
                <p className="text-[11px] text-ink-muted">Pair Repetition</p>
                <p className="mt-0.5 text-base font-extrabold text-ink-primary">
                  +{explainedChannel.explanation.breakdown.pairRepetitionScore} pts
                </p>
              </div>
              <div className="rounded-badge bg-surface-muted p-3">
                <p className="text-[11px] text-ink-muted">Narrative Weight</p>
                <p className="mt-0.5 text-base font-extrabold text-ink-primary">
                  +{explainedChannel.explanation.breakdown.narrativeWeightScore} pts
                </p>
              </div>
            </div>

            <div className="space-y-1.5 text-xs">
              <p>
                <strong className="text-ink-primary">Biggest Score Driver:</strong>{' '}
                {explainedChannel.explanation.breakdown.dominantFactor}
              </p>
              <p>
                <strong className="text-ink-primary">Co-Moving Channels:</strong>{' '}
                {explainedChannel.explanation.coMovingChannels.join(', ')}
              </p>
              <p>
                <strong className="text-ink-primary">Dominant Narrative:</strong>{' '}
                {explainedChannel.explanation.dominantNarrativeCategory}
              </p>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}

