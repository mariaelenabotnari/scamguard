import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import type { IDashboardService } from '../../../services/dashboard.service';
import { DashboardPage } from './DashboardPage';

describe('DashboardPage (Overview, Needs Attention, Activity Chart & Widgets)', () => {
  it('renders Overview header, 4 KPI stat cards, Needs Attention, timeline chart, and widgets', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /^overview$/i }),
      ).toBeInTheDocument();
    });

    // 4 KPI stat cards with consistent integer values
    expect(screen.getByText('Channels watched')).toBeInTheDocument();
    expect(screen.getByText('312')).toBeInTheDocument();
    expect(screen.getByText('305 active, 7 paused')).toBeInTheDocument();

    expect(screen.getByText('Messages analysed')).toBeInTheDocument();
    expect(screen.getByText('24,514')).toBeInTheDocument();

    expect(screen.getByText('Clusters found')).toBeInTheDocument();
    expect(screen.getByText('48')).toBeInTheDocument();

    expect(screen.getByText('High-risk channels')).toBeInTheDocument();
    expect(screen.getByText('14')).toBeInTheDocument();

    // Needs attention block
    expect(screen.getByRole('heading', { name: /needs attention/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /top clusters needing attention/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /riskiest channels/i })).toBeInTheDocument();

    // Timeline chart
    expect(screen.getByRole('heading', { name: /messages and flagged clusters/i })).toBeInTheDocument();
    expect(
      screen.getByRole('img', { name: /coordinated activity timeline chart/i }),
    ).toBeInTheDocument();

    // Bottom widgets
    expect(screen.getByRole('heading', { name: /narrative distribution/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /latest alerts & system status/i })).toBeInTheDocument();
  });

  it('updates overview data when global range is switched in Topbar', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('24,514')).toBeInTheDocument();
    });

    // Switch range via Topbar select
    const rangeSelect = screen.getByLabelText(/analysis time range/i);
    fireEvent.change(rangeSelect, { target: { value: '24h' } });

    await waitFor(() => {
      expect(screen.getByText('3,502')).toBeInTheDocument();
      expect(screen.getByText('8')).toBeInTheDocument();
    });

    // Switch to 30d
    fireEvent.change(rangeSelect, { target: { value: '30d' } });

    await waitFor(() => {
      expect(screen.getByText('98,240')).toBeInTheDocument();
      expect(screen.getByText('184')).toBeInTheDocument();
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
