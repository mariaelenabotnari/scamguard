import type { RiskBand, ScoreExplanationDto } from './ranking.dto';

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
  status: 'active' | 'paused';
  addedAt: string;
  addedBy: string;
  score: number;
  riskBand: RiskBand;
  scoreHistory: readonly ChannelScoreHistoryPointDto[];
  explanation: ScoreExplanationDto;
  coMovingChannels: readonly CoMovingChannelDto[];
  joinedClusters: readonly ChannelJoinedClusterDto[];
}
