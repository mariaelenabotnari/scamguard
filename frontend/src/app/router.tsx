import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AdminSettingsPage } from '../features/admin/pages/AdminSettingsPage';
import { AlertsPage } from '../features/alerts/pages/AlertsPage';
import { LoginPage } from '../features/auth/pages/LoginPage';
import { RegisterPage } from '../features/auth/pages/RegisterPage';
import { UnauthorizedPage } from '../features/auth/pages/UnauthorizedPage';
import { ChannelDetailPage } from '../features/channels/pages/ChannelDetailPage';
import { ClusterComparePage } from '../features/clusters/pages/ClusterComparePage';
import { ClustersListPage } from '../features/clusters/pages/ClustersListPage';
import { DashboardPage } from '../features/dashboard/pages/DashboardPage';
import { NotFoundPage } from '../features/misc/pages/NotFoundPage';
import { RiskRankingPage } from '../features/ranking/pages/RiskRankingPage';
import { SearchPage } from '../features/search/pages/SearchPage';
import { StyleguidePage } from '../features/styleguide/pages/StyleguidePage';
import { WatchlistPage } from '../features/watchlist/pages/WatchlistPage';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/channels" element={<WatchlistPage />} />
      <Route path="/channels/:channelId" element={<ChannelDetailPage />} />
      <Route path="/clusters" element={<ClustersListPage />} />
      <Route path="/clusters/:clusterId" element={<ClusterComparePage />} />
      <Route path="/admin" element={<AdminSettingsPage />} />
      <Route path="/search" element={<SearchPage />} />
      <Route path="/ranking" element={<RiskRankingPage />} />
      <Route path="/alerts" element={<AlertsPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/unauthorized" element={<UnauthorizedPage />} />
      <Route path="/styleguide" element={<StyleguidePage />} />
      <Route path="*" element={<NotFoundPage />} />
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
