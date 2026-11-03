import type { NavItemDto, ShellSummaryDto } from '../dtos/layout.dto';

export const PRIMARY_NAV_ITEMS: readonly NavItemDto[] = [
  { id: 'overview', label: 'Overview', path: '/', icon: 'gauge-high' },
  { id: 'clusters', label: 'Clusters', path: '/clusters', icon: 'diagram-project' },
  { id: 'channels', label: 'Channels', path: '/channels', icon: 'tower-broadcast' },
  { id: 'alerts', label: 'Alerts', path: '/alerts', icon: 'bell', badgeCount: 3 },
  { id: 'settings', label: 'Settings', path: '/admin', icon: 'gear', adminOnly: true },
];

export const MOCK_SHELL_SUMMARY: ShellSummaryDto = {
  lastCollectionLabel: '14:02 Today • Active',
  unreadAlertsCount: 3,
  user: {
    fullName: 'Elena Botnari',
    roleLabel: 'Lead Researcher',
    role: 'admin',
    initials: 'EB',
  },
  pulseBars: [
    { id: 'b1', label: '10:00', heightPercent: 48 },
    { id: 'b2', label: '11:00', heightPercent: 88, isHighlighted: true, tag: 'Max' },
    { id: 'b3', label: '12:00', heightPercent: 56 },
    { id: 'b4', label: '13:00', heightPercent: 34, isHighlighted: true, tag: 'Min' },
    { id: 'b5', label: '14:00', heightPercent: 72 },
    { id: 'b6', label: '15:00', heightPercent: 28 },
    { id: 'b7', label: '16:00', heightPercent: 52 },
  ],
  quickCards: [
    {
      id: 'watched-channels',
      label: 'Monitored Channels',
      value: '312',
      targetPath: '/channels',
    },
    {
      id: 'analyzed-messages',
      label: 'Analyzed Today',
      value: '3502',
      targetPath: '/search',
    },
    {
      id: 'active-clusters',
      label: 'Coordinated Clusters',
      value: '48',
      targetPath: '/clusters',
    },
  ],
  calendarDays: [
    { dayShort: 'Mo', dateNumber: 12 },
    { dayShort: 'Tu', dateNumber: 13, isActive: true, hasAlertDot: true },
    { dayShort: 'We', dateNumber: 14 },
    { dayShort: 'Th', dateNumber: 15 },
    { dayShort: 'Fr', dateNumber: 16, hasAlertDot: true },
    { dayShort: 'Sa', dateNumber: 17 },
    { dayShort: 'Su', dateNumber: 18 },
  ],
  audit: {
    title: 'Audit',
    periodLabel: 'Feb 1 to Mar 5',
    primaryPercentage: 75,
    primaryLabel: 'Reviews',
    secondaryPercentage: 38,
    secondaryLabel: 'High-Risk Share',
  },
};
