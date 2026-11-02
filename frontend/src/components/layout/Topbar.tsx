import React from 'react';
import type { SupportedLocale, TimeRangeOption } from '../../dtos/layout.dto';
import { Icon } from '../ui';

export interface TopbarProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  onSearchSubmit: (query: string) => void;
  lastCollectionLabel: string;
  selectedRange: TimeRangeOption;
  onRangeChange: (range: TimeRangeOption) => void;
  locale: SupportedLocale;
  onLocaleChange: (locale: SupportedLocale) => void;
  unreadAlertsCount: number;
  onOpenMobileMenu: () => void;
  onOpenAlerts?: () => void;
}

const LOCALES: readonly SupportedLocale[] = ['EN', 'RO', 'RU'];
const RANGES: readonly TimeRangeOption[] = ['24h', '7d', '30d'];

export function Topbar({
  searchQuery,
  onSearchChange,
  onSearchSubmit,
  lastCollectionLabel,
  selectedRange,
  onRangeChange,
  locale,
  onLocaleChange,
  unreadAlertsCount,
  onOpenMobileMenu,
  onOpenAlerts,
}: TopbarProps) {
  const handleFormSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSearchSubmit(searchQuery);
  };

  const handleCycleLocale = () => {
    const currentIndex = LOCALES.indexOf(locale);
    const nextLocale = LOCALES[(currentIndex + 1) % LOCALES.length];
    onLocaleChange(nextLocale);
  };

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 pb-5">
      {/* Left: Mobile Drawer Trigger + Search Input */}
      <div className="flex flex-1 items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobileMenu}
          aria-label="Open navigation menu"
          className="inline-flex h-10 w-10 items-center justify-center rounded-badge bg-surface-card text-ink-primary shadow-card lg:hidden"
        >
          <Icon name="bars" />
        </button>

        <form
          role="search"
          onSubmit={handleFormSubmit}
          className="flex w-full max-w-md items-center gap-3 rounded-badge bg-transparent px-2 py-1.5"
        >
          <Icon name="magnifying-glass" className="text-sm text-ink-primary" />
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search for Statics..."
            aria-label="Search channels, messages, or clusters"
            className="w-full bg-transparent text-xs font-medium text-ink-primary placeholder:text-ink-muted focus:outline-none"
          />
        </form>
      </div>

      {/* Right: Timestamp & Range Pill, Language Switcher, Alerts Bell */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5 rounded-badge bg-surface-card px-3.5 py-2 shadow-card">
          <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-brand-700 text-white">
            <Icon name="clock" className="text-[10px]" />
          </span>
          <span className="hidden text-[11px] font-medium text-ink-muted sm:inline">
            {lastCollectionLabel}
          </span>
          <select
            aria-label="Analysis time range"
            value={selectedRange}
            onChange={(e) => onRangeChange(e.target.value as TimeRangeOption)}
            className="rounded-md bg-surface-muted px-2 py-0.5 text-[11px] font-bold text-ink-primary focus:outline-none"
          >
            {RANGES.map((range) => (
              <option key={range} value={range}>
                {range}
              </option>
            ))}
          </select>
        </div>

        <button
          type="button"
          onClick={handleCycleLocale}
          aria-label={`Switch language (current: ${locale})`}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-ink-muted transition-colors hover:text-ink-primary"
        >
          <span>{locale}</span>
          <Icon name="chevron-down" className="text-[10px]" />
        </button>

        <button
          type="button"
          onClick={onOpenAlerts}
          aria-label={`Notifications (${unreadAlertsCount} unread)`}
          className="relative inline-flex h-9 w-9 items-center justify-center rounded-full text-ink-primary transition-colors hover:bg-surface-banner"
        >
          <Icon name="bell" className="text-sm" />
          {unreadAlertsCount > 0 ? (
            <span
              aria-hidden="true"
              className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-status-dangerText ring-2 ring-surface-app"
            />
          ) : null}
        </button>
      </div>
    </header>
  );
}
