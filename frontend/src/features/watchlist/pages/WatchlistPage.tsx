import React, { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
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
  Tabs,
} from '../../../components/ui';
import type { WatchlistChannelDto } from '../../../dtos/channel.dto';
import { channelService, type IChannelService } from '../../../services/channel.service';
import { ExportModal } from '../../export/components/ExportModal';
import { Sparkline } from '../../ranking/components/Sparkline';

export interface WatchlistPageProps {
  service?: IChannelService;
}

type ChannelTabFilter = 'all' | 'high_risk';

export function WatchlistPage({ service = channelService }: WatchlistPageProps) {
  const [searchParams] = useSearchParams();
  const [channels, setChannels] = useState<readonly WatchlistChannelDto[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeTab, setActiveTab] = useState<ChannelTabFilter>(
    searchParams.get('tab') === 'high-risk' ? 'high_risk' : 'all',
  );
  const [showAddForm, setShowAddForm] = useState<boolean>(false);
  const [activeWhyChannelId, setActiveWhyChannelId] = useState<string | null>(null);

  // Add channel form state
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
      setShowAddForm(false);
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

  const filteredChannels = channels.filter((channel) => {
    if (activeTab === 'high_risk' && (channel.score ?? 0) < 70) {
      return false;
    }
    if (!searchQuery.trim()) {
      return true;
    }
    const q = searchQuery.toLowerCase();
    return (
      channel.handle.toLowerCase().includes(q) ||
      channel.title.toLowerCase().includes(q) ||
      channel.primaryNarrative?.toLowerCase().includes(q)
    );
  });

  const highRiskCount = channels.filter((c) => (c.score ?? 0) >= 70).length;

  const tabOptions = [
    { value: 'all' as ChannelTabFilter, label: `All Watched (${channels.length})` },
    { value: 'high_risk' as ChannelTabFilter, label: `High Risk Only (${highRiskCount})` },
  ];

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Compact Page Header */}
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary">
              Channels
            </h1>
            <p className="mt-0.5 text-xs font-medium text-ink-muted">
              Monitor risk scores, coordination participation, and watchlist status across tracked Telegram channels.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <ExportModal defaultEntity="channels" />
            <Button
              variant="primary"
              size="sm"
              leftIcon="plus"
              onClick={() => setShowAddForm((prev) => !prev)}
            >
              Track New Channel
            </Button>
          </div>
        </div>

        {/* Add Channel Form Card (Accessible both via click or inline) */}
        <Card className={`transition-all ${showAddForm ? 'block' : 'block'}`}>
          <form onSubmit={(e) => void handleAddChannel(e)} className="space-y-3" noValidate>
            <div className="flex items-center justify-between border-b border-brand-100 pb-2">
              <h2 className="text-sm font-bold text-ink-primary">
                Add Public Channel to Watchlist
              </h2>
              <span className="text-[11px] text-ink-muted">Telegram handle or t.me link</span>
            </div>

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

        {/* Search & Tabs Filter Bar */}
        <Card padding="sm" className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="w-full sm:max-w-sm">
            <Input
              aria-label="Filter channels"
              placeholder="Search by name, @handle or narrative..."
              leftIcon="magnifying-glass"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Tabs
            ariaLabel="Channels risk filter"
            variant="soft"
            items={tabOptions}
            value={activeTab}
            onChange={setActiveTab}
          />
        </Card>

        {/* Channels Full-Width Table */}
        {isLoading ? (
          <div aria-label="Loading channels" className="space-y-3">
            <Skeleton variant="block" className="h-16 w-full" />
            <Skeleton variant="block" className="h-16 w-full" />
            <Skeleton variant="block" className="h-16 w-full" />
          </div>
        ) : filteredChannels.length === 0 ? (
          <EmptyState
            icon="tower-broadcast"
            title="No Channels Found"
            description={
              searchQuery
                ? `No channels matched "${searchQuery}".`
                : 'No channels match the selected risk filter.'
            }
          />
        ) : (
          <section aria-label="Watched channels list" className="space-y-3">
            <div className="overflow-x-auto rounded-card border border-brand-100 bg-surface-card shadow-card">
              <table className="w-full text-left border-collapse" aria-label="Watched channels table">
                <thead>
                  <tr className="border-b border-brand-100 bg-surface-muted/50 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
                    <th className="px-5 py-3.5">Channel</th>
                    <th className="px-4 py-3.5">Risk Score</th>
                    <th className="px-4 py-3.5">Main Narrative</th>
                    <th className="px-4 py-3.5 text-center">Clusters Joined</th>
                    <th className="px-4 py-3.5">7d Trend</th>
                    <th className="px-4 py-3.5">Status</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-100/60 text-xs">
                  {filteredChannels.map((channel) => {
                    const isHighRisk = (channel.score ?? 0) >= 70;
                    const isMediumRisk = (channel.score ?? 0) >= 40 && (channel.score ?? 0) < 70;
                    const isWhyOpen = activeWhyChannelId === channel.id;

                    return (
                      <tr
                        key={channel.id}
                        className="transition-colors hover:bg-surface-banner/30"
                      >
                        {/* Channel Column */}
                        <td className="px-5 py-3.5">
                          <div className="flex items-center gap-3">
                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 font-bold text-xs text-brand-800">
                              {channel.handle.slice(1, 3).toUpperCase()}
                            </div>
                            <div className="min-w-0">
                              <Link
                                to={`/channels/${channel.id}`}
                                className="font-bold text-ink-primary hover:text-brand-700 hover:underline block truncate max-w-[200px]"
                              >
                                {channel.title}
                              </Link>
                              <div className="flex items-center gap-2 text-[11px] text-ink-muted">
                                <span className="font-semibold text-brand-700">{channel.handle}</span>
                                <span>•</span>
                                <span>{channel.subscribersCount.toLocaleString()} subs</span>
                              </div>
                            </div>
                          </div>
                        </td>

                        {/* Risk Score Column with "Why?" Link */}
                        <td className="px-4 py-3.5">
                          <div className="relative inline-block">
                            <div className="flex items-center gap-2">
                              <Badge
                                variant={isHighRisk ? 'high' : isMediumRisk ? 'medium' : 'low'}
                              >
                                {isHighRisk ? 'HIGH' : isMediumRisk ? 'MEDIUM' : 'LOW'} {channel.score}
                              </Badge>
                              <button
                                type="button"
                                onClick={() =>
                                  setActiveWhyChannelId(isWhyOpen ? null : channel.id)
                                }
                                className="text-[11px] font-bold text-brand-700 underline hover:text-brand-800 focus:outline-none"
                              >
                                Why?
                              </button>
                            </div>

                            {/* Popover explaining the score */}
                            {isWhyOpen ? (
                              <div
                                role="dialog"
                                aria-label={`Risk explanation for ${channel.handle}`}
                                className="absolute left-0 top-8 z-30 w-72 rounded-card border border-brand-200 bg-surface-card p-3 shadow-shell"
                              >
                                <div className="flex items-start justify-between gap-2 border-b border-brand-100 pb-2">
                                  <span className="text-[11px] font-bold text-ink-primary">
                                    Why score is {channel.score}?
                                  </span>
                                  <button
                                    type="button"
                                    onClick={() => setActiveWhyChannelId(null)}
                                    className="text-ink-muted hover:text-ink-primary"
                                  >
                                    <Icon name="xmark" className="text-xs" />
                                  </button>
                                </div>
                                <p className="mt-2 text-[11px] leading-relaxed text-ink-secondary">
                                  {channel.whyExplanation ||
                                    `Channel participates in coordinated cascades with high frequency and low median delay.`}
                                </p>
                                <div className="mt-2 text-right">
                                  <Link
                                    to={`/channels/${channel.id}`}
                                    className="text-[10px] font-bold text-brand-700 hover:underline"
                                  >
                                    Inspect full breakdown →
                                  </Link>
                                </div>
                              </div>
                            ) : null}
                          </div>
                        </td>

                        {/* Main Narrative Column */}
                        <td className="px-4 py-3.5">
                          <span className="block max-w-[220px] truncate text-xs font-semibold text-ink-primary">
                            {channel.primaryNarrative || 'General news'}
                          </span>
                        </td>

                        {/* Clusters Joined Column */}
                        <td className="px-4 py-3.5 text-center font-bold text-ink-primary">
                          {channel.clustersJoinedCount ?? 0}
                        </td>

                        {/* 7d Sparkline Column */}
                        <td className="px-4 py-3.5">
                          {channel.sparkline ? (
                            <Sparkline
                              values={channel.sparkline}
                              riskBand={channel.riskBand}
                              label={`${channel.handle} 7-day risk trend`}
                            />
                          ) : (
                            <span className="text-ink-muted">—</span>
                          )}
                        </td>

                        {/* Status Column */}
                        <td className="px-4 py-3.5">
                          <Badge
                            variant={channel.status === 'active' ? 'success' : 'medium'}
                            icon={channel.status === 'active' ? 'circle-check' : 'clock'}
                          >
                            {channel.status === 'active' ? 'Active' : 'Paused'}
                          </Badge>
                        </td>

                        {/* Actions Column */}
                        <td className="px-5 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Link to={`/channels/${channel.id}`}>
                              <Button variant="secondary" size="sm">
                                Inspect
                              </Button>
                            </Link>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => void handleToggleStatus(channel.id)}
                              aria-label={`${
                                channel.status === 'active' ? 'Pause' : 'Resume'
                              } ${channel.handle}`}
                            >
                              <Icon
                                name={channel.status === 'active' ? 'pause' : 'play'}
                                className="text-xs mr-1"
                              />
                              {channel.status === 'active' ? 'Pause' : 'Resume'}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => void handleRemove(channel.id)}
                              aria-label={`Remove ${channel.handle}`}
                            >
                              <Icon name="trash" className="text-xs text-status-dangerText mr-1" />
                              Remove
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>
    </AppShell>
  );
}
