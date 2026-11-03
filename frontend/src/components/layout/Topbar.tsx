import React, { useEffect, useRef, useState } from 'react';
import type {
  SupportedLocale,
  TimeRangeOption,
  UserProfileSummaryDto,
} from '../../dtos/layout.dto';
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
  user?: UserProfileSummaryDto;
  onSignOut?: () => void;
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
  user,
  onSignOut,
  onOpenMobileMenu,
  onOpenAlerts,
}: TopbarProps) {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
          className="flex w-full max-w-md items-center gap-3 rounded-badge bg-surface-card px-3.5 py-2 shadow-card"
        >
          <Icon name="magnifying-glass" className="text-sm text-ink-muted" />
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search channels, messages or clusters..."
            aria-label="Search channels, messages, or clusters"
            className="w-full bg-transparent text-xs font-medium text-ink-primary placeholder:text-ink-muted focus:outline-none"
          />
        </form>
      </div>

      {/* Right Controls: Global Range, Language Switcher, Alerts Bell, User Menu */}
      <div className="flex items-center gap-3">
        {/* Global Date Range */}
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
            className="cursor-pointer rounded-md bg-surface-muted px-2 py-0.5 text-[11px] font-bold text-ink-primary focus:outline-none"
          >
            {RANGES.map((range) => (
              <option key={range} value={range}>
                {range}
              </option>
            ))}
          </select>
        </div>

        {/* Language Switch */}
        <button
          type="button"
          onClick={handleCycleLocale}
          aria-label={`Switch language (current: ${locale})`}
          className="inline-flex items-center gap-1.5 rounded-badge bg-surface-card px-2.5 py-2 text-xs font-semibold text-ink-muted shadow-card transition-colors hover:text-ink-primary"
        >
          <span>{locale}</span>
          <Icon name="chevron-down" className="text-[10px]" />
        </button>

        {/* Alerts Bell */}
        <button
          type="button"
          onClick={onOpenAlerts}
          aria-label={`Notifications (${unreadAlertsCount} unread)`}
          className="relative inline-flex h-9 w-9 items-center justify-center rounded-full bg-surface-card text-ink-primary shadow-card transition-colors hover:bg-surface-banner"
        >
          <Icon name="bell" className="text-sm" />
          {unreadAlertsCount > 0 ? (
            <span
              aria-hidden="true"
              className="absolute right-1 top-1 flex h-2 w-2 rounded-full bg-status-dangerText ring-2 ring-surface-app"
            />
          ) : null}
        </button>

        {/* User Profile Avatar & Menu */}
        {user ? (
          <div ref={userMenuRef} className="relative">
            <button
              type="button"
              onClick={() => setIsUserMenuOpen((prev) => !prev)}
              aria-label={`User menu for ${user.fullName}`}
              aria-expanded={isUserMenuOpen}
              className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-brand-800 text-xs font-bold text-white shadow-card transition-all hover:ring-2 hover:ring-brand-400"
            >
              {user.initials}
            </button>

            {isUserMenuOpen ? (
              <div
                role="menu"
                aria-label="User account actions"
                className="absolute right-0 top-11 z-30 w-52 rounded-card border border-brand-100 bg-surface-card p-3 shadow-card animate-in fade-in zoom-in-95"
              >
                <div className="border-b border-brand-100/60 pb-2.5">
                  <p className="truncate text-xs font-bold text-ink-primary">
                    {user.fullName}
                  </p>
                  <p className="truncate text-[11px] font-medium text-ink-muted">
                    {user.roleLabel}
                  </p>
                  <span className="mt-1.5 inline-block rounded-full bg-brand-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-brand-700">
                    {user.role}
                  </span>
                </div>

                <div className="pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      onSignOut?.();
                    }}
                    role="menuitem"
                    className="flex w-full items-center gap-2 rounded-badge px-2.5 py-1.5 text-xs font-semibold text-status-dangerText transition-colors hover:bg-status-dangerBg"
                  >
                    <Icon name="right-from-bracket" className="text-xs" />
                    <span>Sign out</span>
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </header>
  );
}
