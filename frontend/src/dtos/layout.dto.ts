import type { IconName } from '../components/ui';

export type TimeRangeOption = '24h' | '7d' | '30d';
export type SupportedLocale = 'EN' | 'RO' | 'RU';
export type UserRole = 'visitor' | 'journalist' | 'admin';

export interface NavItemDto {
  id: string;
  label: string;
  path: string;
  icon: IconName;
  badgeCount?: number;
}

export interface SidebarPulseBarDto {
  id: string;
  label: string;
  heightPercent: number;
  isHighlighted?: boolean;
  tag?: 'Max' | 'Min';
}

export interface QuickSummaryCardDto {
  id: string;
  label: string;
  value: string;
  targetPath: string;
}

export interface CalendarDayDto {
  dayShort: string;
  dateNumber: number;
  isActive?: boolean;
  hasAlertDot?: boolean;
}

export interface AuditGaugeDto {
  title: string;
  periodLabel: string;
  primaryPercentage: number;
  primaryLabel: string;
  secondaryPercentage: number;
  secondaryLabel: string;
}

export interface UserProfileSummaryDto {
  fullName: string;
  roleLabel: string;
  role: UserRole;
  initials: string;
}

export interface ShellSummaryDto {
  lastCollectionLabel: string;
  unreadAlertsCount: number;
  user: UserProfileSummaryDto;
  pulseBars: readonly SidebarPulseBarDto[];
  quickCards: readonly QuickSummaryCardDto[];
  calendarDays: readonly CalendarDayDto[];
  audit: AuditGaugeDto;
}
