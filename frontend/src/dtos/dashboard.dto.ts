import type { IconName } from '../components/ui';
import type { TimeRangeOption } from './layout.dto';

export type StatCardTone = 'lavender' | 'cyan' | 'peach' | 'rose';
export type TrendDirection = 'up' | 'down';

export interface StatCardMetricDto {
  id: string;
  label: string;
  formattedValue: string;
  numericValue: number;
  deltaPercent: number;
  formattedDelta: string;
  trendDirection: TrendDirection;
  icon: IconName;
  tone: StatCardTone;
  subline?: string;
  targetPath?: string;
}

export interface DashboardBannerDto {
  greetingTitle: string;
  subtitle: string;
  activeChannelsCount: number;
  parameterVersion: string;
}

export interface TimelinePointDto {
  id: string;
  axisLabel: string;
  dateLabel: string;
  messagesCount: number;
  flaggedClustersCount: number;
  formattedHeadline: string;
  normalizedY: number;
  isHighlighted?: boolean;
}

export interface ActivityTimelineDto {
  title: string;
  subtitle: string;
  range: TimeRangeOption;
  points: readonly TimelinePointDto[];
}

export interface TopClusterItemDto {
  id: string;
  headline: string;
  narrativeCategory: string;
  channelsCount: number;
  timeWindow: string;
  postedAtLabel: string;
}

export interface RiskiestChannelItemDto {
  id: string;
  handle: string;
  title: string;
  score: number;
  riskBand: 'high' | 'medium' | 'low';
  sparkline: readonly number[];
  primaryNarrative: string;
}

export interface NarrativeCountItemDto {
  category: string;
  clustersCount: number;
  percentage: number;
}

export interface SystemStatusDto {
  lastCollectionLabel: string;
  nextRunLabel: string;
  connectionStatus: 'ok' | 'degraded' | 'error';
  analysisDelaySeconds: number;
}

export interface DashboardOverviewDto {
  range: TimeRangeOption;
  banner: DashboardBannerDto;
  timeline: ActivityTimelineDto;
  stats: readonly StatCardMetricDto[];
  topClusters?: readonly TopClusterItemDto[];
  riskiestChannels?: readonly RiskiestChannelItemDto[];
  narrativeCounts?: readonly NarrativeCountItemDto[];
  systemStatus?: SystemStatusDto;
}
