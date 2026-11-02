import { BrowserRouter, Link, Route, Routes } from 'react-router-dom';
import { AppShell } from '../components/layout';
import { Badge, Button, Card } from '../components/ui';
import { AlertsPage } from '../features/alerts/pages/AlertsPage';
import { ChannelDetailPage } from '../features/channels/pages/ChannelDetailPage';
import { ClusterComparePage } from '../features/clusters/pages/ClusterComparePage';
import { ClustersListPage } from '../features/clusters/pages/ClustersListPage';
import { DashboardPage } from '../features/dashboard/pages/DashboardPage';
import { RiskRankingPage } from '../features/ranking/pages/RiskRankingPage';
import { StyleguidePage } from '../features/styleguide/pages/StyleguidePage';

interface SectionPlaceholderProps {
  title: string;
  subtitle: string;
}

function SectionPlaceholder({ title, subtitle }: SectionPlaceholderProps) {
  return (
    <AppShell>
      <div className="space-y-6">
        <Card
          tone="banner"
          padding="lg"
          className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"
        >
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary">{title}</h1>
            <p className="mt-1 text-xs font-medium text-ink-muted">{subtitle}</p>
          </div>
          <Badge variant="brand" icon="shield-halved">
            Scamguard Monitor
          </Badge>
        </Card>

        <Card className="space-y-3">
          <p className="text-sm text-ink-secondary">
            Coordinated Telegram channel activity detection and narrative analysis workspace.
          </p>
          <div>
            <Link to="/styleguide">
              <Button variant="secondary" size="sm" rightIcon="arrow-right">
                View Design System Styleguide
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route
        path="/channels"
        element={
          <SectionPlaceholder
            title="Monitored Channels"
            subtitle="Watchlist management and channel coordination profiles"
          />
        }
      />
      <Route path="/channels/:channelId" element={<ChannelDetailPage />} />
      <Route path="/clusters" element={<ClustersListPage />} />
      <Route path="/clusters/:clusterId" element={<ClusterComparePage />} />
      <Route
        path="/admin"
        element={
          <SectionPlaceholder
            title="Threshold & System Settings"
            subtitle="Versioned similarity parameters and collection intervals"
          />
        }
      />
      <Route
        path="/search"
        element={
          <SectionPlaceholder
            title="Messages & Narrative Search"
            subtitle="Full-text and semantic query across monitored Telegram posts"
          />
        }
      />
      <Route path="/ranking" element={<RiskRankingPage />} />
      <Route path="/alerts" element={<AlertsPage />} />
      <Route path="/styleguide" element={<StyleguidePage />} />
    </Routes>
  );
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
