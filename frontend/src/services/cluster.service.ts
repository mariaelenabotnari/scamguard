import type {
  ClusterDetailDto,
  ClusterFilterDto,
  ClusterSummaryDto,
} from '../dtos/cluster.dto';
import { httpClient, isMockMode, type IHttpClient } from '../lib/api/http-client';
import {
  DEFAULT_CLUSTER_DETAIL,
  MOCK_CLUSTERS,
  NARRATIVE_CATEGORIES,
} from '../mocks/cluster.mock';

export interface IClusterService {
  getClusters(filter?: ClusterFilterDto): Promise<readonly ClusterSummaryDto[]>;
  getClusterDetail(clusterId: string): Promise<ClusterDetailDto>;
  getNarrativeCategories(): readonly string[];
}

export class ClusterService implements IClusterService {
  constructor(private readonly client: IHttpClient = httpClient) {}

  getNarrativeCategories(): readonly string[] {
    return NARRATIVE_CATEGORIES;
  }

  async getClusters(filter: ClusterFilterDto = {}): Promise<readonly ClusterSummaryDto[]> {
    const { category = 'all', query = '' } = filter;

    if (isMockMode()) {
      const normalizedQuery = query.trim().toLowerCase();
      const filtered = MOCK_CLUSTERS.filter((cluster) => {
        const matchesCategory =
          !category || category === 'all' || cluster.narrativeCategory === category;
        const matchesQuery =
          !normalizedQuery ||
          cluster.headlineSummary.toLowerCase().includes(normalizedQuery) ||
          cluster.representativeSnippet.toLowerCase().includes(normalizedQuery) ||
          cluster.narrativeCategory.toLowerCase().includes(normalizedQuery) ||
          cluster.participants.some((p) =>
            p.handle.toLowerCase().includes(normalizedQuery),
          );
        return matchesCategory && matchesQuery;
      });
      return Promise.resolve(filtered);
    }

    const params = new URLSearchParams();
    if (category && category !== 'all') params.set('category', category);
    if (query.trim()) params.set('q', query.trim());
    const qs = params.toString();
    return this.client.get<readonly ClusterSummaryDto[]>(
      `/clusters${qs ? `?${qs}` : ''}`,
    );
  }

  async getClusterDetail(clusterId: string): Promise<ClusterDetailDto> {
    if (isMockMode()) {
      const summary = MOCK_CLUSTERS.find((c) => c.id === clusterId) ?? MOCK_CLUSTERS[0];
      return Promise.resolve({
        ...DEFAULT_CLUSTER_DETAIL,
        summary,
      });
    }
    return this.client.get<ClusterDetailDto>(`/clusters/${clusterId}`);
  }
}

export const clusterService: IClusterService = new ClusterService();
