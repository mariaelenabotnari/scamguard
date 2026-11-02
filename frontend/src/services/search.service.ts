import type { UnifiedSearchResultsDto } from '../dtos/search.dto';
import { httpClient, isMockMode, type IHttpClient } from '../lib/api/http-client';
import { MOCK_CLUSTERS } from '../mocks/cluster.mock';
import { MOCK_RANKED_CHANNELS } from '../mocks/ranking.mock';
import { MOCK_SEARCH_MESSAGES } from '../mocks/search.mock';

export interface ISearchService {
  searchAll(query: string): Promise<UnifiedSearchResultsDto>;
}

export class SearchService implements ISearchService {
  constructor(private readonly client: IHttpClient = httpClient) {}

  async searchAll(query: string): Promise<UnifiedSearchResultsDto> {
    const normalized = query.trim().toLowerCase();

    if (isMockMode()) {
      const channels = MOCK_RANKED_CHANNELS.filter(
        (ch) =>
          !normalized ||
          ch.handle.toLowerCase().includes(normalized) ||
          ch.title.toLowerCase().includes(normalized) ||
          ch.primaryNarrative.toLowerCase().includes(normalized),
      );

      const messages = MOCK_SEARCH_MESSAGES.filter(
        (msg) =>
          !normalized ||
          msg.snippet.toLowerCase().includes(normalized) ||
          msg.handle.toLowerCase().includes(normalized) ||
          msg.narrativeCategory.toLowerCase().includes(normalized),
      );

      const clusters = MOCK_CLUSTERS.filter(
        (cl) =>
          !normalized ||
          cl.headlineSummary.toLowerCase().includes(normalized) ||
          cl.representativeSnippet.toLowerCase().includes(normalized) ||
          cl.narrativeCategory.toLowerCase().includes(normalized),
      );

      return Promise.resolve({
        query: query.trim(),
        channels,
        messages,
        clusters,
      });
    }

    const qs = normalized ? `?q=${encodeURIComponent(query.trim())}` : '';
    return this.client.get<UnifiedSearchResultsDto>(`/search${qs}`);
  }
}

export const searchService: ISearchService = new SearchService();
