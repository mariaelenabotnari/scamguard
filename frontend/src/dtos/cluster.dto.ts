export type ClusterMatchType = 'exact' | 'minhash' | 'semantic';

export interface ClusterChannelParticipantDto {
  channelId: string;
  handle: string;
  title: string;
  initials: string;
  postedAt: string;
  delaySeconds: number;
  similarityScore: number;
}

export interface ClusterSummaryDto {
  id: string;
  headlineSummary: string;
  representativeSnippet: string;
  narrativeCategory: string;
  narrativeConfidence: number;
  channelsCount: number;
  spanMinutes: number;
  firstPostedAt: string;
  lastPostedAt: string;
  averageSimilarity: number;
  matchType: ClusterMatchType;
  parameterVersion: string;
  participants: readonly ClusterChannelParticipantDto[];
}

export interface ClusterFilterDto {
  category?: string;
  query?: string;
}
