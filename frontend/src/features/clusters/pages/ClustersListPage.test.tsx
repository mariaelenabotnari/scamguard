import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppRoutes } from '../../../app/router';
import type { IClusterService } from '../../../services/cluster.service';
import { ClustersListPage } from './ClustersListPage';

describe('ClustersListPage (feat/fe-clusters-list)', () => {
  it('renders detected clusters with N channels in M minutes headline, narrative tags, first/last times, and channel avatars', async () => {
    render(
      <MemoryRouter initialEntries={['/clusters']}>
        <AppRoutes />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByRole('heading', {
          name: /same message posted by 5 channels in 8 minutes/i,
        }),
      ).toBeInTheDocument();
    });

    // Verify narrative category tags
    expect(
      screen.getAllByText('Sanctions, energy prices and economy fear').length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByText('Moldova government and elections delegitimisation').length,
    ).toBeGreaterThanOrEqual(1);

    // Verify first/last timestamps and channel avatar stack (+1 overflow on 5-channel cluster)
    expect(screen.getByText('2026-11-02 13:14')).toBeInTheDocument();
    expect(screen.getByText('2026-11-02 13:22')).toBeInTheDocument();
    expect(screen.getByLabelText('1 more channels')).toBeInTheDocument();

    // Navigate to cluster comparison view
    const compareButtons = screen.getAllByRole('button', { name: /compare messages/i });
    fireEvent.click(compareButtons[0]);
    expect(
      await screen.findByLabelText(/side-by-side message comparison/i),
    ).toBeInTheDocument();
  });

  it('filters clusters by narrative category and search query', async () => {
    render(
      <MemoryRouter>
        <ClustersListPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/same message posted by 5 channels in 8 minutes/i),
      ).toBeInTheDocument();
    });

    // Filter by narrative category
    const categorySelect = screen.getByLabelText(/filter by narrative category/i);
    fireEvent.change(categorySelect, {
      target: { value: 'Transnistria / Gagauzia and separatism' },
    });

    await waitFor(() => {
      expect(
        screen.getByText(/same message posted by 3 channels in 5 minutes/i),
      ).toBeInTheDocument();
      expect(
        screen.queryByText(/same message posted by 5 channels in 8 minutes/i),
      ).not.toBeInTheDocument();
    });

    // Reset category and filter by search query
    fireEvent.change(categorySelect, { target: { value: 'all' } });
    const searchInput = screen.getByLabelText(/search clusters/i);
    fireEvent.change(searchInput, { target: { value: 'бюллетеней' } });

    await waitFor(() => {
      expect(
        screen.getByText(/same message posted by 4 channels in 11 minutes/i),
      ).toBeInTheDocument();
      expect(
        screen.queryByText(/same message posted by 3 channels in 5 minutes/i),
      ).not.toBeInTheDocument();
    });
  });

  it('renders error state when cluster service fails', async () => {
    const failingService: IClusterService = {
      getNarrativeCategories: () => [],
      getClusters: () => Promise.reject(new Error('Cluster service unavailable')),
      getClusterDetail: () => Promise.reject(new Error('Cluster service unavailable')),
    };

    render(
      <MemoryRouter>
        <ClustersListPage service={failingService} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/unable to load coordinated clusters/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/cluster service unavailable/i)).toBeInTheDocument();
    });
  });
});

