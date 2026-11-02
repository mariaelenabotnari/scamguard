import { useState } from 'react';
import { AppShell } from '../../../components/layout';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Select,
  Skeleton,
} from '../../../components/ui';
import type { IClusterService } from '../../../services/cluster.service';
import { ClustersList } from '../components/ClustersList';
import { useClustersList } from '../hooks/useClustersList';

export interface ClustersListPageProps {
  service?: IClusterService;
}

export function ClustersListPage({ service }: ClustersListPageProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const { clusters, categories, isLoading, error, reload } = useClustersList(
    selectedCategory,
    searchQuery,
    service,
  );

  const categoryOptions = [
    { value: 'all', label: 'All Disinformation Narratives' },
    ...categories.map((cat) => ({ value: cat, label: cat })),
  ];

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
              Detected Coordinated Clusters
            </h1>
            <p className="mt-1 text-xs font-medium text-ink-muted">
              Near-duplicate and semantically equivalent messages posted across multiple channels
              within a short time window
            </p>
          </div>
          <Badge variant="brand" icon="layer-group">
            Threshold ≥ 0.85 • 60m Window
          </Badge>
        </Card>

        {/* Search & Narrative Category Filter Bar */}
        <Card padding="sm" className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Input
            aria-label="Search clusters"
            placeholder="Search by message snippet, @channel, or keyword..."
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
            title="Unable to Load Coordinated Clusters"
            description={error}
            action={
              <Button variant="primary" size="sm" leftIcon="rotate-right" onClick={reload}>
                Retry
              </Button>
            }
          />
        ) : (
          <ClustersList clusters={clusters} />
        )}
      </div>
    </AppShell>
  );
}

