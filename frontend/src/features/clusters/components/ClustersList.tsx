import { EmptyState } from '../../../components/ui';
import type { ClusterSummaryDto } from '../../../dtos/cluster.dto';
import { ClusterCard } from './ClusterCard';

export interface ClustersListProps {
  clusters: readonly ClusterSummaryDto[];
}

export function ClustersList({ clusters }: ClustersListProps) {
  if (clusters.length === 0) {
    return (
      <EmptyState
        icon="layer-group"
        title="No Coordinated Clusters Found"
        description="No multi-channel message clusters matched the current narrative category or search filter."
      />
    );
  }

  return (
    <section aria-label="Detected message clusters" className="space-y-4">
      {clusters.map((cluster) => (
        <ClusterCard key={cluster.id} cluster={cluster} />
      ))}
    </section>
  );
}

