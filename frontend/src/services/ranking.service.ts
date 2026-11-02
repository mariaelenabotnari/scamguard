import type { RankedChannelDto, RiskRankingFilterDto } from '../dtos/ranking.dto';
import { httpClient, isMockMode, type IHttpClient } from '../lib/api/http-client';
import { MOCK_RANKED_CHANNELS } from '../mocks/ranking.mock';

export interface IRankingService {
  getRankedChannels(filter?: RiskRankingFilterDto): Promise<readonly RankedChannelDto[]>;
}

export class RankingService implements IRankingService {
  constructor(private readonly client: IHttpClient = httpClient) {}

  async getRankedChannels(
    filter: RiskRankingFilterDto = {},
  ): Promise<readonly RankedChannelDto[]> {
    const { riskBand = 'all', query = '' } = filter;

    if (isMockMode()) {
      const normalizedQuery = query.trim().toLowerCase();
      const filtered = MOCK_RANKED_CHANNELS.filter((channel) => {
        const matchesBand = riskBand === 'all' || channel.riskBand === riskBand;
        const matchesQuery =
          !normalizedQuery ||
          channel.handle.toLowerCase().includes(normalizedQuery) ||
          channel.title.toLowerCase().includes(normalizedQuery) ||
          channel.primaryNarrative.toLowerCase().includes(normalizedQuery);
        return matchesBand && matchesQuery;
      });

      return Promise.resolve([...filtered].sort((a, b) => b.score - a.score));
    }

    const params = new URLSearchParams();
    if (riskBand !== 'all') params.set('risk_band', riskBand);
    if (query.trim()) params.set('q', query.trim());
    const qs = params.toString();
    return this.client.get<readonly RankedChannelDto[]>(
      `/channels/ranking${qs ? `?${qs}` : ''}`,
    );
  }
}

export const rankingService: IRankingService = new RankingService();
