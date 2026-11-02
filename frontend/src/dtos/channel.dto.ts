import type { RiskBand, ScoreExplanationDto } from './ranking.dto';

export type WatchlistStatus = 'active' | 'paused';

export interface WatchlistChannelDto {
  id: string;
  handle: string;
  title: string;
  language: 'RO' | 'RU' | 'MIXED';
  status: WatchlistStatus;
  addedBy: string;
  addedAt: string;
  subscribersCount: number;
}

export interface AddWatchlistChannelInputDto {
  handleOrUrl: string;
  title: string;
  language: 'RO' | 'RU' | 'MIXED';
}

export interface CoMovingChannelDto {
  channelId: string;
  handle: string;
  title: string;
  sharedClustersCount: number;
  medianTimeDiffSeconds: number;
  averageSimilarity: number;
}

export interface ChannelJoinedClusterDto {
  clusterId: string;
  headlineSummary: string;
  narrativeCategory: string;
  postedAt: string;
  delaySeconds: number;
  similarityScore: number;
}

export interface ChannelScoreHistoryPointDto {
  dateLabel: string;
  score: number;
}

export interface ChannelDetailDto {
  id: string;
  handle: string;
  title: string;
  language: 'RO' | 'RU' | 'MIXED';
  subscribersCount: number;
  status: WatchlistStatus;
  addedAt: string;
  addedBy: string;
  score: number;
  riskBand: RiskBand;
  scoreHistory: readonly ChannelScoreHistoryPointDto[];
  explanation: ScoreExplanationDto;
  coMovingChannels: readonly CoMovingChannelDto[];
  joinedClusters: readonly ChannelJoinedClusterDto[];
}
