import { useState } from 'react';
import { AppShell } from '../../../components/layout';
import {
  Button,
  Card,
  EmptyState,
  Input,
  Select,
  Skeleton,
} from '../../../components/ui';
import type { IClusterService } from '../../../services/cluster.service';
import { ExportModal } from '../../export/components/ExportModal';
import { ClustersList } from '../components/ClustersList';
import { useClustersList } from '../hooks/useClustersList';

export interface ClustersListPageProps {
  service?: IClusterService;
}

export function ClustersListPage({ service }: ClustersListPageProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [minChannels, setMinChannels] = useState<string>('3');
  const [sortBy, setSortBy] = useState<string>('channels');

  const { clusters, categories, isLoading, error, reload } = useClustersList(
    selectedCategory,
    searchQuery,
    service,
  );

  const categoryOptions = [
    { value: 'all', label: 'All Disinformation Narratives' },
    ...categories.map((cat) => ({ value: cat, label: cat })),
  ];

  const minChannelsOptions = [
    { value: '2', label: 'Min 2+ Channels' },
    { value: '3', label: 'Min 3+ Channels (Default)' },
    { value: '4', label: 'Min 4+ Channels' },
    { value: '5', label: 'Min 5+ Channels' },
  ];

  const sortOptions = [
    { value: 'channels', label: 'Most Channels' },
    { value: 'newest', label: 'Newest First' },
    { value: 'speed', label: 'Fastest Spread' },
  ];

  const filteredClusters = clusters
    .filter((cl) => {
      const minN = parseInt(minChannels, 10) || 2;
      return cl.participants.length >= minN;
    })
    .sort((a, b) => {
      if (sortBy === 'channels') {
        return b.participants.length - a.participants.length;
      }
      if (sortBy === 'speed') {
        return a.spanMinutes - b.spanMinutes;
      }
      return b.firstPostedAt.localeCompare(a.firstPostedAt);
    });

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary">
              Clusters
            </h1>
            <p className="mt-0.5 text-xs font-medium text-ink-muted">
              A cluster is one message, or near copies of it, that several channels posted within a short time.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <ExportModal defaultEntity="clusters" />
          </div>
        </div>

        {/* Filter Bar: Search, Narrative, Min Channels, Sort */}
        <Card padding="sm" className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            aria-label="Search clusters"
            placeholder="Search cluster text or keyword..."
            leftIcon="magnifying-glass"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <Select
            aria-label="Filter by narrative category"
            options={categoryOptions}
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
          />
          <Select
            aria-label="Filter by minimum channels"
            options={minChannelsOptions}
            value={minChannels}
            onChange={(e) => setMinChannels(e.target.value)}
          />
          <Select
            aria-label="Sort clusters"
            options={sortOptions}
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          />
        </Card>

        {/* Clusters Feed */}
        {isLoading ? (
          <div aria-label="Loading detected clusters" className="space-y-4">
            <Skeleton variant="block" className="h-44 w-full" />
            <Skeleton variant="block" className="h-44 w-full" />
          </div>
        ) : error ? (
          <EmptyState
            icon="triangle-exclamation"
            title="Unable to Load Clusters"
            description={error}
            action={
              <Button variant="primary" size="sm" leftIcon="rotate-right" onClick={reload}>
                Retry
              </Button>
            }
          />
        ) : filteredClusters.length === 0 ? (
          <EmptyState
            icon="diagram-project"
            title="No Clusters Found"
            description={
              searchQuery
                ? `No clusters matched "${searchQuery}".`
                : 'No clusters matched the current narrative and channel filters.'
            }
          />
        ) : (
          <ClustersList clusters={filteredClusters} />
        )}
      </div>
    </AppShell>
  );
}
