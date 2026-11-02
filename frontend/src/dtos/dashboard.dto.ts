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

export interface DashboardOverviewDto {
  range: TimeRangeOption;
  banner: DashboardBannerDto;
  timeline: ActivityTimelineDto;
  stats: readonly StatCardMetricDto[];
}
