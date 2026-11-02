import type { ClusterSummaryDto } from './cluster.dto';
import type { RankedChannelDto, RiskBand, ScoreExplanationDto } from './ranking.dto';

export interface SearchMessageHitDto {
  id: string;
  channelId: string;
  handle: string;
  postedAt: string;
  snippet: string;
  narrativeCategory: string;
  clusterId: string | null;
  channelScore: number;
  riskBand: RiskBand;
  explanation: ScoreExplanationDto;
}

export interface UnifiedSearchResultsDto {
  query: string;
  channels: readonly RankedChannelDto[];
  messages: readonly SearchMessageHitDto[];
  clusters: readonly ClusterSummaryDto[];
}
