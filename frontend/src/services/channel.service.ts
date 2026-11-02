import type {
  AddWatchlistChannelInputDto,
  ChannelDetailDto,
  WatchlistChannelDto,
} from '../dtos/channel.dto';
import { httpClient, isMockMode, type IHttpClient } from '../lib/api/http-client';
import {
  DEFAULT_MOCK_CHANNEL_DETAIL,
  MOCK_CHANNEL_DETAILS,
  MOCK_WATCHLIST_CHANNELS,
} from '../mocks/channel.mock';

export function normalizeTelegramHandle(rawInput: string): string | null {
  const trimmed = rawInput.trim();
  const urlMatch = /^(?:https?:\/\/)?t\.me\/([a-zA-Z0-9_]{5,32})\/?$/.exec(trimmed);
  if (urlMatch) {
    return `@${urlMatch[1]}`;
  }
  const handleMatch = /^@([a-zA-Z0-9_]{5,32})$/.exec(trimmed);
  if (handleMatch) {
    return `@${handleMatch[1]}`;
  }
  return null;
}

export interface IChannelService {
  getChannelDetail(channelId: string): Promise<ChannelDetailDto>;
  getWatchlist(): Promise<readonly WatchlistChannelDto[]>;
  addWatchlistChannel(input: AddWatchlistChannelInputDto): Promise<WatchlistChannelDto>;
  toggleWatchlistStatus(channelId: string): Promise<WatchlistChannelDto>;
  removeWatchlistChannel(channelId: string): Promise<void>;
}

export class ChannelService implements IChannelService {
  private watchlistStore: WatchlistChannelDto[] = [...MOCK_WATCHLIST_CHANNELS];

  constructor(private readonly client: IHttpClient = httpClient) {}

  async getChannelDetail(channelId: string): Promise<ChannelDetailDto> {
    if (isMockMode()) {
      const found = MOCK_CHANNEL_DETAILS[channelId] ?? {
        ...DEFAULT_MOCK_CHANNEL_DETAIL,
        id: channelId,
      };
      return Promise.resolve(found);
    }
    return this.client.get<ChannelDetailDto>(`/channels/${channelId}`);
  }

  async getWatchlist(): Promise<readonly WatchlistChannelDto[]> {
    if (isMockMode()) {
      return Promise.resolve([...this.watchlistStore]);
    }
    return this.client.get<readonly WatchlistChannelDto[]>('/watchlist');
  }

  async addWatchlistChannel(
    input: AddWatchlistChannelInputDto,
  ): Promise<WatchlistChannelDto> {
    const normalizedHandle = normalizeTelegramHandle(input.handleOrUrl);
    if (!normalizedHandle) {
      return Promise.reject(
        new Error(
          'Invalid Telegram username. Use @channel_name or https://t.me/channel_name (5–32 characters).',
        ),
      );
    }

    if (isMockMode()) {
      const exists = this.watchlistStore.some(
        (ch) => ch.handle.toLowerCase() === normalizedHandle.toLowerCase(),
      );
      if (exists) {
        return Promise.reject(
          new Error(`Channel ${normalizedHandle} is already on the watch list.`),
        );
      }

      const newEntry: WatchlistChannelDto = {
        id: `ch-${normalizedHandle.slice(1).toLowerCase()}`,
        handle: normalizedHandle,
        title: input.title.trim() || normalizedHandle,
        language: input.language,
        status: 'active',
        addedBy: 'elena.botnari',
        addedAt: '2026-11-02',
        subscribersCount: 1200,
      };
      this.watchlistStore = [newEntry, ...this.watchlistStore];
      return Promise.resolve(newEntry);
    }

    return this.client.post<AddWatchlistChannelInputDto, WatchlistChannelDto>(
      '/watchlist',
      input,
    );
  }

  async toggleWatchlistStatus(channelId: string): Promise<WatchlistChannelDto> {
    if (isMockMode()) {
      const index = this.watchlistStore.findIndex((c) => c.id === channelId);
      if (index === -1) {
        return Promise.reject(new Error('Channel not found on watch list.'));
      }
      const current = this.watchlistStore[index];
      const updated: WatchlistChannelDto = {
        ...current,
        status: current.status === 'active' ? 'paused' : 'active',
      };
      this.watchlistStore[index] = updated;
      return Promise.resolve(updated);
    }
    return this.client.post<Record<string, never>, WatchlistChannelDto>(
      `/watchlist/${channelId}/toggle`,
      {},
    );
  }

  async removeWatchlistChannel(channelId: string): Promise<void> {
    if (isMockMode()) {
      this.watchlistStore = this.watchlistStore.filter((c) => c.id !== channelId);
      return Promise.resolve();
    }
    await this.client.post<Record<string, never>, unknown>(
      `/watchlist/${channelId}/remove`,
      {},
    );
  }
}

export const channelService: IChannelService = new ChannelService();
