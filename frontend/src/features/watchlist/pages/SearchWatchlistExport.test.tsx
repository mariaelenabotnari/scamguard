import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { ChannelService } from '../../../services/channel.service';
import { ExportService } from '../../../services/export.service';
import { SearchService } from '../../../services/search.service';
import { ExportModal } from '../../export/components/ExportModal';
import { SearchPage } from '../../search/pages/SearchPage';
import { WatchlistPage } from './WatchlistPage';

describe('SearchPage, WatchlistPage, and ExportModal (Branch 2 of 3)', () => {
  it('renders unified search results with NFR-13 score explanations and filters by query', async () => {
    const searchService = new SearchService();
    render(
      <MemoryRouter initialEntries={['/search']}>
        <SearchPage service={searchService} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByLabelText('Matching channels')).toBeInTheDocument();
    });

    // Verify NFR-13 explanation text is rendered alongside search results
    expect(screen.getAllByText(/Score Explanation/i).length).toBeGreaterThan(0);

    const searchInput = screen.getByLabelText('Search channels, messages, and clusters');
    fireEvent.change(searchInput, { target: { value: 'nonexistent_query_xyz' } });

    await waitFor(() => {
      expect(screen.getByText('No Matching Records')).toBeInTheDocument();
    });
  });

  it('validates handles, adds a channel, toggles active/paused, and removes a channel on WatchlistPage', async () => {
    const channelService = new ChannelService();
    render(
      <MemoryRouter initialEntries={['/channels']}>
        <WatchlistPage service={channelService} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByLabelText('Watched channels list')).toBeInTheDocument();
    });

    const handleInput = screen.getByLabelText('Telegram Handle or URL');
    const submitBtn = screen.getByRole('button', { name: /add channel/i });

    // Submit invalid handle
    fireEvent.change(handleInput, { target: { value: 'bad' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/Invalid Telegram username/i),
      ).toBeInTheDocument();
    });

    // Submit valid handle
    fireEvent.change(handleInput, { target: { value: 'https://t.me/moldova_observer_md' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getAllByText('@moldova_observer_md').length).toBeGreaterThan(0);
    });

    // Toggle status (Pause)
    const pauseBtn = screen.getByRole('button', { name: 'Pause @moldova_observer_md' });
    fireEvent.click(pauseBtn);

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Resume @moldova_observer_md' }),
      ).toBeInTheDocument();
    });

    // Remove channel
    const removeBtn = screen.getByRole('button', { name: 'Remove @moldova_observer_md' });
    fireEvent.click(removeBtn);

    await waitFor(() => {
      expect(
        screen.queryByRole('button', { name: 'Resume @moldova_observer_md' }),
      ).not.toBeInTheDocument();
    });
  });

  it('displays NFR-10 export limits and triggers CSV export in ExportModal', async () => {
    const exportService = new ExportService();
    render(<ExportModal defaultEntity="clusters" service={exportService} />);

    fireEvent.click(screen.getByRole('button', { name: /export data/i }));

    await waitFor(() => {
      expect(screen.getByText(/Account Export Quota \(NFR-10\)/i)).toBeInTheDocument();
      expect(screen.getByText('250 rows')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /generate csv export/i }));

    await waitFor(() => {
      expect(screen.getByLabelText('Export confirmation receipt')).toBeInTheDocument();
    });
  });
});
