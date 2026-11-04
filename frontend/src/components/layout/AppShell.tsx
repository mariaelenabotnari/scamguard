import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type {
  ShellSummaryDto,
  SupportedLocale,
  TimeRangeOption,
} from '../../dtos/layout.dto';
import { isMockMode } from '../../lib/api/http-client';
import { MOCK_SHELL_SUMMARY } from '../../mocks/layout.mock';
import { authService } from '../../services/auth.service';
import { layoutService } from '../../services/layout.service';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

const INITIAL_SHELL_SUMMARY: ShellSummaryDto = {
  lastCollectionLabel: 'Syncing...',
  unreadAlertsCount: 0,
  user: {
    fullName: 'ScamGuard Analyst',
    roleLabel: 'Surveillance Desk',
    role: 'admin',
    initials: 'SA',
  },
  pulseBars: [],
  quickCards: [
    {
      id: 'watched-channels',
      label: 'Monitored Channels',
      value: '0',
      targetPath: '/channels',
    },
    {
      id: 'analyzed-messages',
      label: 'Analyzed Messages',
      value: '0',
      targetPath: '/search',
    },
    {
      id: 'active-clusters',
      label: 'Coordinated Clusters',
      value: '0',
      targetPath: '/clusters',
    },
  ],
  calendarDays: [],
  audit: {
    title: 'Live Surveillance',
    periodLabel: 'System Status',
    primaryPercentage: 100,
    primaryLabel: 'Audit Coverage',
    secondaryPercentage: 100,
    secondaryLabel: 'Pipeline Precision',
  },
};

export interface AppShellProps {
  children: React.ReactNode;
  selectedRange?: TimeRangeOption;
  onRangeChange?: (range: TimeRangeOption) => void;
}

export function AppShell({
  children,
  selectedRange: controlledRange,
  onRangeChange,
}: AppShellProps) {
  const navigate = useNavigate();
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [internalRange, setInternalRange] = useState<TimeRangeOption>('7d');
  const [locale, setLocale] = useState<SupportedLocale>('EN');
  const [summary, setSummary] = useState<ShellSummaryDto>(() =>
    isMockMode() ? MOCK_SHELL_SUMMARY : INITIAL_SHELL_SUMMARY,
  );

  const activeRange = controlledRange ?? internalRange;
  const navItems = layoutService.getNavItems();

  useEffect(() => {
    let isMounted = true;
    layoutService
      .getShellSummary()
      .then((data) => {
        if (isMounted) {
          setSummary(data);
        }
      })
      .catch(() => {
        // Fallback to initial summary state on error
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleRangeChange = (nextRange: TimeRangeOption) => {
    setInternalRange(nextRange);
    onRangeChange?.(nextRange);
  };

  const handleSearchSubmit = (query: string) => {
    const trimmed = query.trim();
    if (trimmed) {
      navigate(`/search?q=${encodeURIComponent(trimmed)}`);
    } else {
      navigate('/search');
    }
  };

  const handleSignOut = async () => {
    await authService.logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-surface-canvas p-2 sm:p-5 lg:p-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-[1440px] flex-col overflow-hidden rounded-shell bg-surface-app shadow-shell lg:flex-row">
        {/* Left Navigation Column */}
        <Sidebar
          items={navItems}
          userRole={summary.user.role}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
          isMobileOpen={isMobileMenuOpen}
          onCloseMobile={() => setIsMobileMenuOpen(false)}
        />

        {/* Full-width Main Workspace Column */}
        <div className="flex min-w-0 flex-1 flex-col px-5 py-6 sm:px-8">
          <Topbar
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onSearchSubmit={handleSearchSubmit}
            lastCollectionLabel={summary.lastCollectionLabel}
            selectedRange={activeRange}
            onRangeChange={handleRangeChange}
            locale={locale}
            onLocaleChange={setLocale}
            unreadAlertsCount={summary.unreadAlertsCount}
            user={summary.user}
            onSignOut={handleSignOut}
            onOpenMobileMenu={() => setIsMobileMenuOpen(true)}
            onOpenAlerts={() => navigate('/alerts')}
          />

          <main className="flex-1">{children}</main>
        </div>
      </div>
    </div>
  );
}
