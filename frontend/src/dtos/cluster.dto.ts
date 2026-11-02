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

export interface DiffTokenDto {
  text: string;
  isChanged?: boolean;
}

export interface ClusterMessagePostDto {
  id: string;
  channelId: string;
  handle: string;
  channelTitle: string;
  postedAt: string;
  delaySeconds: number;
  similarityToAnchor: number;
  isDeletedAtSource: boolean;
  originalUrl: string | null;
  rawText: string | null;
  normalizedText: string;
  textHash: string;
  diffTokens: readonly DiffTokenDto[];
}

export interface ClusterDetailDto {
  summary: ClusterSummaryDto;
  posts: readonly ClusterMessagePostDto[];
}
