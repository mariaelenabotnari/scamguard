import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import type { IDashboardService } from '../../../services/dashboard.service';
import { DashboardPage } from './DashboardPage';

describe('DashboardPage (Overview & Timeline Chart)', () => {
  it('renders greeting banner, timeline chart with callout, and all 4 KPI stat cards', async () => {
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

    // Timeline chart title, SVG plot, and default highlighted callout
    expect(screen.getByRole('heading', { name: /profile growth/i })).toBeInTheDocument();
    expect(
      screen.getByRole('img', { name: /coordinated activity timeline chart/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId('timeline-callout')).toHaveTextContent('11 of September');
    expect(screen.getByTestId('timeline-callout')).toHaveTextContent('12,301 msgs');

    // Click another timeline axis bucket (Sat) and verify callout updates
    fireEvent.click(screen.getByRole('button', { name: 'Sat' }));
    expect(screen.getByTestId('timeline-callout')).toHaveTextContent('15 of September');
    expect(screen.getByTestId('timeline-callout')).toHaveTextContent('14,200 msgs');

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

  it('updates timeline chart and KPI stat card values when switching range between 7d, 24h, and 30d', async () => {
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
      expect(screen.getByTestId('timeline-callout')).toHaveTextContent('Today 04:00');
      expect(screen.getByTestId('timeline-callout')).toHaveTextContent('890 msgs • 4 clusters');
    });

    // Switch to 30d tab
    fireEvent.click(screen.getByRole('tab', { name: '30d' }));

    await waitFor(() => {
      expect(screen.getByText('194,310')).toBeInTheDocument();
      expect(screen.getByTestId('timeline-callout')).toHaveTextContent('Week 4 (Oct)');
      expect(screen.getByTestId('timeline-callout')).toHaveTextContent('42,800 msgs • 41 clusters');
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
