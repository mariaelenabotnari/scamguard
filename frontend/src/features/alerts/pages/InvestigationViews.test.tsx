import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppRoutes } from '../../../app/router';

describe('Investigation Views (AlertsPage, ChannelDetailPage, ClusterComparePage)', () => {
  it('renders AlertsPage with severity filter and dismisses an alert', async () => {
    render(
      <MemoryRouter initialEntries={['/alerts']}>
        <AppRoutes />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /rapid 5-channel burst on energy tariffs/i }),
      ).toBeInTheDocument();
    });

    // Dismiss the first alert
    const dismissBtn = screen.getByRole('button', {
      name: /dismiss alert rapid 5-channel burst on energy tariffs/i,
    });
    fireEvent.click(dismissBtn);

    await waitFor(() => {
      expect(
        screen.queryByRole('heading', { name: /rapid 5-channel burst on energy tariffs/i }),
      ).not.toBeInTheDocument();
    });
  });

  it('renders ChannelDetailPage with score history, explanation block, co-moving channels, and joined clusters', async () => {
    render(
      <MemoryRouter initialEntries={['/channels/ch-moldova-pulse']}>
        <AppRoutes />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: '@moldova_news_pulse' }),
      ).toBeInTheDocument();
    });

    // Score & Explanation block (FR-07, NFR-13)
    expect(screen.getByText('HIGH RISK • 91/100')).toBeInTheDocument();
    expect(screen.getByTestId('channel-explanation-block')).toHaveTextContent(
      'Flagged due to high cluster participation',
    );
    expect(screen.getByText('+34 pts')).toBeInTheDocument();

    // Co-moving channels and joined clusters
    expect(screen.getByText('@gagauzia_voice_md')).toBeInTheDocument();
    expect(
      screen.getByText(/same message posted by 5 channels in 8 minutes/i),
    ).toBeInTheDocument();
  });

  it('renders ClusterComparePage with highlighted differences and deleted-post NFR-11 state', async () => {
    render(
      <MemoryRouter initialEntries={['/clusters/cl-energy-winter-01']}>
        <AppRoutes />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByLabelText(/side-by-side message comparison/i),
      ).toBeInTheDocument();
    });

    // Highlighted diff token in second post
    expect(screen.getByText('majorate cu 100% din 15 noiembrie')).toBeInTheDocument();

    // Deleted post state (NFR-11 / UC-02: raw text purged, normalised text + hash shown)
    const deletedPostBlock = screen.getByTestId('deleted-post-post-103');
    expect(deletedPostBlock).toHaveTextContent(
      'Original no longer available at source (Deleted Post)',
    );
    expect(deletedPostBlock).toHaveTextContent(
      'срочно тарифы на газ и электроэнергию будут удвоены',
    );
    expect(
      screen.getByText('sha256:7d12f04e89a6c3105b4d2e9901f8a3c4'),
    ).toBeInTheDocument();
  });
});

