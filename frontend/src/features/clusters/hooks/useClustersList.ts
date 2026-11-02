import { useCallback, useEffect, useState } from 'react';
import type { ClusterSummaryDto } from '../../../dtos/cluster.dto';
import {
  clusterService,
  type IClusterService,
} from '../../../services/cluster.service';

export interface UseClustersListResult {
  clusters: readonly ClusterSummaryDto[];
  categories: readonly string[];
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

export function useClustersList(
  category: string,
  query: string,
  service: IClusterService = clusterService,
): UseClustersListResult {
  const [clusters, setClusters] = useState<readonly ClusterSummaryDto[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const categories = service.getNarrativeCategories();

  const load = useCallback(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    service
      .getClusters({ category, query })
      .then((result) => {
        if (isMounted) {
          setClusters(result);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const message =
            err instanceof Error ? err.message : 'Failed to load detected clusters.';
          setError(message);
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [category, query, service]);

  useEffect(() => {
    const cleanup = load();
    return cleanup;
  }, [load]);

  return {
    clusters,
    categories,
    isLoading,
    error,
    reload: load,
  };
}

