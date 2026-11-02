import { useState } from 'react';
import { AppShell } from '../../../components/layout';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Skeleton,
  Tabs,
} from '../../../components/ui';
import type { RiskBand } from '../../../dtos/ranking.dto';
import type { IRankingService } from '../../../services/ranking.service';
import { RiskRankingTable } from '../components/RiskRankingTable';
import { useRiskRanking } from '../hooks/useRiskRanking';

export interface RiskRankingPageProps {
  service?: IRankingService;
}

const BAND_TABS: readonly { value: RiskBand | 'all'; label: string }[] = [
  { value: 'all', label: 'All Channels' },
  { value: 'high', label: 'High Risk' },
  { value: 'medium', label: 'Medium Risk' },
  { value: 'low', label: 'Low Risk' },
];

export function RiskRankingPage({ service }: RiskRankingPageProps) {
  const [selectedBand, setSelectedBand] = useState<RiskBand | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const { channels, isLoading, error, reload } = useRiskRanking(
    selectedBand,
    searchQuery,
    service,
  );

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Page Header Banner */}
        <Card
          tone="banner"
          padding="lg"
          className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"
        >
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary">
              Coordination Risk Ranking
            </h1>
            <p className="mt-1 text-xs font-medium text-ink-muted">
              Channels sorted by composite coordination risk score (0–100) with transparent factor
              explanations
            </p>
          </div>
          <Badge variant="brand" icon="shield-halved">
            Parameter Version v3
          </Badge>
        </Card>

        {/* Filter Bar */}
        <Card padding="sm" className="flex flex-wrap items-center justify-between gap-4">
          <div className="w-full sm:max-w-xs">
            <Input
              aria-label="Filter ranked channels"
              placeholder="Filter by @handle, title, or narrative..."
              leftIcon="magnifying-glass"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Tabs
            ariaLabel="Risk band filter"
            variant="soft"
            items={BAND_TABS}
            value={selectedBand}
            onChange={setSelectedBand}
          />
        </Card>

        {/* Main Ranking Content */}
        {isLoading ? (
          <div aria-label="Loading channel risk ranking" className="space-y-3">
            <Skeleton variant="block" className="h-16 w-full" />
            <Skeleton variant="block" className="h-16 w-full" />
            <Skeleton variant="block" className="h-16 w-full" />
          </div>
        ) : error ? (
          <EmptyState
            icon="triangle-exclamation"
            title="Unable to Load Risk Ranking"
            description={error}
            action={
              <Button variant="primary" size="sm" leftIcon="rotate-right" onClick={reload}>
                Retry
              </Button>
            }
          />
        ) : (
          <RiskRankingTable channels={channels} />
        )}
      </div>
    </AppShell>
  );
}

