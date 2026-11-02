export type RiskBand = 'low' | 'medium' | 'high';

export interface ScoreFactorBreakdownDto {
  clusterShareScore: number;
  copyDelayScore: number;
  pairRepetitionScore: number;
  narrativeWeightScore: number;
  dominantFactor: string;
}

export interface ScoreExplanationDto {
  summary: string;
  parameterVersion: string;
  participatingClustersCount: number;
  coMovingChannels: readonly string[];
  medianCopyDelaySeconds: number;
  dominantNarrativeCategory: string;
  breakdown: ScoreFactorBreakdownDto;
}

export interface RankedChannelDto {
  id: string;
  handle: string;
  title: string;
  language: 'RO' | 'RU' | 'MIXED';
  subscribersCount: number;
  score: number;
  riskBand: RiskBand;
  sparkline: readonly number[];
  clustersJoinedCount: number;
  primaryNarrative: string;
  explanation: ScoreExplanationDto;
}

export interface RiskRankingFilterDto {
  riskBand?: RiskBand | 'all';
  query?: string;
}
