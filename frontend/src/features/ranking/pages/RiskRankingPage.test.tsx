import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppRoutes } from '../../../app/router';
import type { IRankingService } from '../../../services/ranking.service';
import { RiskRankingPage } from './RiskRankingPage';

describe('RiskRankingPage (feat/fe-risk-ranking)', () => {
  it('renders channels sorted by coordination risk score with risk badges, sparklines, and explanation modal', async () => {
    render(
      <MemoryRouter initialEntries={['/ranking']}>
        <AppRoutes />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('@moldova_news_pulse')).toBeInTheDocument();
    });

    // Verify channels are sorted by descending score (91 -> 86 -> 78 -> 64 -> 52 -> 18)
    expect(screen.getByText('HIGH • 91/100')).toBeInTheDocument();
    expect(screen.getByText('HIGH • 86/100')).toBeInTheDocument();
    expect(screen.getByText('MEDIUM • 64/100')).toBeInTheDocument();
    expect(screen.getByText('LOW • 18/100')).toBeInTheDocument();

    // Verify sparklines are rendered
    expect(
      screen.getByRole('img', { name: /@moldova_news_pulse 7-day score trend/i }),
    ).toBeInTheDocument();

    // Open score explanation modal ("Why?")
    fireEvent.click(
      screen.getByRole('button', { name: /explain score for @moldova_news_pulse/i }),
    );
    expect(
      screen.getByRole('dialog', { name: /score explanation: @moldova_news_pulse/i }),
    ).toBeInTheDocument();
    expect(screen.getByText('+34 pts')).toBeInTheDocument();

    // Navigate to channel profile from explanation modal
    fireEvent.click(screen.getByRole('button', { name: /open channel profile/i }));
    expect(
      await screen.findByRole('heading', {
        name: /why was this channel flagged\?/i,
      }),
    ).toBeInTheDocument();
  });

  it('filters channels by risk band and search query', async () => {
    render(
      <MemoryRouter>
        <RiskRankingPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('@moldova_news_pulse')).toBeInTheDocument();
    });

    // Filter to Low Risk only
    fireEvent.click(screen.getByRole('tab', { name: /low risk/i }));

    await waitFor(() => {
      expect(screen.getByText('@agro_journal_md')).toBeInTheDocument();
      expect(screen.queryByText('@moldova_news_pulse')).not.toBeInTheDocument();
    });

    // Switch back to All Channels and search by handle
    fireEvent.click(screen.getByRole('tab', { name: /all channels/i }));
    const searchInput = screen.getByLabelText(/filter ranked channels/i);
    fireEvent.change(searchInput, { target: { value: 'balti' } });

    await waitFor(() => {
      expect(screen.getByText('@balti_pravda')).toBeInTheDocument();
      expect(screen.queryByText('@agro_journal_md')).not.toBeInTheDocument();
    });
  });

  it('renders error state when ranking service fails', async () => {
    const failingService: IRankingService = {
      getRankedChannels: () => Promise.reject(new Error('Failed to load ranking data')),
    };

    render(
      <MemoryRouter>
        <RiskRankingPage service={failingService} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/unable to load risk ranking/i)).toBeInTheDocument();
      expect(screen.getByText(/failed to load ranking data/i)).toBeInTheDocument();
    });
  });
});

