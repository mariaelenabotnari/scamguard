import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AppShell } from '../../../components/layout';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Icon,
  Input,
  Select,
  Skeleton,
} from '../../../components/ui';
import type { WatchlistChannelDto } from '../../../dtos/channel.dto';
import { channelService, type IChannelService } from '../../../services/channel.service';
import { ExportModal } from '../../export/components/ExportModal';

export interface WatchlistPageProps {
  service?: IChannelService;
}

export function WatchlistPage({ service = channelService }: WatchlistPageProps) {
  const [channels, setChannels] = useState<readonly WatchlistChannelDto[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [handleInput, setHandleInput] = useState<string>('');
  const [titleInput, setTitleInput] = useState<string>('');
  const [languageInput, setLanguageInput] = useState<'RO' | 'RU' | 'MIXED'>('RO');
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const loadWatchlist = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await service.getWatchlist();
      setChannels(response);
    } finally {
      setIsLoading(false);
    }
  }, [service]);

  useEffect(() => {
    void loadWatchlist();
  }, [loadWatchlist]);

  const handleAddChannel = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    setIsSubmitting(true);
    try {
      const created = await service.addWatchlistChannel({
        handleOrUrl: handleInput,
        title: titleInput,
        language: languageInput,
      });
      setChannels((prev) => [created, ...prev]);
      setHandleInput('');
      setTitleInput('');
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Unable to add channel.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (channelId: string) => {
    const updated = await service.toggleWatchlistStatus(channelId);
    setChannels((prev) => prev.map((ch) => (ch.id === channelId ? updated : ch)));
  };

  const handleRemove = async (channelId: string) => {
    await service.removeWatchlistChannel(channelId);
    setChannels((prev) => prev.filter((ch) => ch.id !== channelId));
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <Card
          tone="banner"
          padding="lg"
          className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"
        >
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary">
              Monitored Telegram Watchlist
            </h1>
            <p className="mt-1 text-xs font-medium text-ink-muted">
              Add, pause, or remove public Moldovan Telegram channels tracked by the collector
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            <Badge variant="brand" icon="satellite-dish">
              {channels.filter((c) => c.status === 'active').length} Active Channels
            </Badge>
            <ExportModal defaultEntity="channels" />
          </div>
        </Card>

        <Card>
          <form onSubmit={(e) => void handleAddChannel(e)} className="space-y-3" noValidate>
            <h2 className="text-sm font-bold text-ink-primary">
              Add Public Channel to Watchlist
            </h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-12">
              <div className="sm:col-span-5">
                <Input
                  label="Telegram Handle or URL"
                  placeholder="@moldova_news_md or https://t.me/moldova_news_md"
                  leftIcon="telegram"
                  value={handleInput}
                  onChange={(e) => setHandleInput(e.target.value)}
                  error={formError ?? undefined}
                />
              </div>
              <div className="sm:col-span-3">
                <Input
                  label="Display Title (optional)"
                  placeholder="Moldova News MD"
                  value={titleInput}
                  onChange={(e) => setTitleInput(e.target.value)}
                />
              </div>
              <div className="sm:col-span-2">
                <Select
                  label="Language"
                  value={languageInput}
                  onChange={(e) =>
                    setLanguageInput(e.target.value as 'RO' | 'RU' | 'MIXED')
                  }
                  options={[
                    { value: 'RO', label: 'RO' },
                    { value: 'RU', label: 'RU' },
                    { value: 'MIXED', label: 'MIXED' },
                  ]}
                />
              </div>
              <div className="flex items-end sm:col-span-2">
                <Button
                  type="submit"
                  variant="primary"
                  leftIcon="plus"
                  isLoading={isSubmitting}
                  className="w-full"
                >
                  Add Channel
                </Button>
              </div>
            </div>
          </form>
        </Card>

        {isLoading ? (
          <div aria-label="Loading watchlist" className="space-y-3">
            <Skeleton variant="block" className="h-20 w-full" />
            <Skeleton variant="block" className="h-20 w-full" />
          </div>
        ) : channels.length === 0 ? (
          <EmptyState
            icon="satellite-dish"
            title="Watchlist Is Empty"
            description="Add a public Telegram channel handle above to begin collecting posts."
          />
        ) : (
          <section aria-label="Watched channels list" className="space-y-3">
            {channels.map((channel) => (
              <Card
                key={channel.id}
                padding="md"
                className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"
              >
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link
                      to={`/channels/${channel.id}`}
                      className="text-sm font-bold text-ink-primary hover:text-brand-600"
                    >
                      {channel.title}
                    </Link>
                    <span className="text-xs font-semibold text-brand-500">
                      {channel.handle}
                    </span>
                    <Badge
                      variant={channel.status === 'active' ? 'success' : 'medium'}
                      icon={channel.status === 'active' ? 'circle-check' : 'clock'}
                    >
                      {channel.status === 'active' ? 'Active' : 'Paused'}
                    </Badge>
                    <Badge variant="neutral">{channel.language}</Badge>
                  </div>
                  <p className="text-xs text-ink-muted">
                    {channel.subscribersCount.toLocaleString()} subscribers • Added by{' '}
                    <strong className="font-bold text-ink-primary">{channel.addedBy}</strong> on{' '}
                    {channel.addedAt}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => void handleToggleStatus(channel.id)}
                    aria-label={`${
                      channel.status === 'active' ? 'Pause' : 'Resume'
                    } ${channel.handle}`}
                  >
                    <Icon
                      name={channel.status === 'active' ? 'pause' : 'play'}
                      className="mr-1"
                    />
                    {channel.status === 'active' ? 'Pause' : 'Resume'}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => void handleRemove(channel.id)}
                    aria-label={`Remove ${channel.handle}`}
                  >
                    <Icon name="trash" className="mr-1 text-status-dangerText" />
                    Remove
                  </Button>
                </div>
              </Card>
            ))}
          </section>
        )}
      </div>
    </AppShell>
  );
}
