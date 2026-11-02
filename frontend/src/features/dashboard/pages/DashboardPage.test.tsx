import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import type { IDashboardService } from '../../../services/dashboard.service';
import { DashboardPage } from './DashboardPage';

describe('DashboardPage (feat/fe-dashboard-overview)', () => {
  it('renders greeting banner and all 4 KPI stat cards with mock metrics and trend deltas', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /hello elena botnari/i }),
      ).toBeInTheDocument();
    });

    // Verify all 4 stat cards and values for default 7d range
    expect(screen.getByText('Watched Channels')).toBeInTheDocument();
    expect(screen.getByText('5,095')).toBeInTheDocument();
    expect(screen.getByText('+33.45%')).toBeInTheDocument();

    expect(screen.getByText('Messages Today')).toBeInTheDocument();
    expect(screen.getByText('47,095')).toBeInTheDocument();
    expect(screen.getByText('-112.45%')).toBeInTheDocument();

    expect(screen.getByText('Active Clusters')).toBeInTheDocument();
    expect(screen.getByText('25.81')).toBeInTheDocument();
    expect(screen.getByText('+62.10%')).toBeInTheDocument();

    expect(screen.getByText('High-Risk Channels')).toBeInTheDocument();
    expect(screen.getByText('45.42')).toBeInTheDocument();
    expect(screen.getByText('+4.46%')).toBeInTheDocument();
  });

  it('updates KPI stat card values when switching range between 7d, 24h, and 30d', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('5,095')).toBeInTheDocument();
    });

    // Switch to 24h tab
    fireEvent.click(screen.getByRole('tab', { name: '24h' }));

    await waitFor(() => {
      expect(screen.getByText('6,840')).toBeInTheDocument();
      expect(screen.getByText('+12.40%')).toBeInTheDocument();
    });

    // Switch to 30d tab
    fireEvent.click(screen.getByRole('tab', { name: '30d' }));

    await waitFor(() => {
      expect(screen.getByText('194,310')).toBeInTheDocument();
      expect(screen.getByText('+74.50%')).toBeInTheDocument();
    });
  });

  it('renders error state when service fails', async () => {
    const failingService: IDashboardService = {
      getOverview: () => Promise.reject(new Error('Network timeout fetching overview')),
    };

    render(
      <MemoryRouter>
        <DashboardPage service={failingService} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/unable to load dashboard overview/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/network timeout fetching overview/i)).toBeInTheDocument();
    });
  });
});

