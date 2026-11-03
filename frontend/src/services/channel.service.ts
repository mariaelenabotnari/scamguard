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
import { authService } from './auth.service';

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
  resetUserWatchlist(): void;
}

export class ChannelService implements IChannelService {
  private watchlistStore: WatchlistChannelDto[] = [...MOCK_WATCHLIST_CHANNELS];
  private userWatchlistStore: WatchlistChannelDto[] = [];

  constructor(private readonly client: IHttpClient = httpClient) {}

  resetUserWatchlist(): void {
    this.userWatchlistStore = [];
  }

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
      if (authService.isCleanProfile()) {
        return Promise.resolve([...this.userWatchlistStore]);
      }
      return Promise.resolve([...this.watchlistStore]);
    }
    const response = await this.client.get<
      readonly WatchlistChannelDto[] | { items: readonly WatchlistChannelDto[] }
    >('/watchlist?page=1&pageSize=300');
    if ('items' in response) {
      return response.items;
    }
    return response;
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
      const isClean = authService.isCleanProfile();
      const currentList = isClean ? this.userWatchlistStore : this.watchlistStore;

      const exists = currentList.some(
        (ch) => ch.handle.toLowerCase() === normalizedHandle.toLowerCase(),
      );
      if (exists) {
        return Promise.reject(
          new Error(`Channel ${normalizedHandle} is already on the watch list.`),
        );
      }

      // Check if handle matches known disinformation/spam channel profiles for demonstration
      const lowerHandle = normalizedHandle.toLowerCase();
      const isKnownDisinfo =
        lowerHandle.includes('gagauz') ||
        lowerHandle.includes('kp_md') ||
        lowerHandle.includes('sputnik') ||
        lowerHandle.includes('pridnestrovie') ||
        lowerHandle.includes('balkan');

      const currentUser = await authService.getCurrentUser();
      const newEntry: WatchlistChannelDto = {
        id: `ch-${normalizedHandle.slice(1).toLowerCase()}`,
        handle: normalizedHandle,
        title: input.title.trim() || normalizedHandle,
        language: input.language,
        status: 'active',
        addedBy: currentUser?.username || currentUser?.fullName || 'investigator',
        addedAt: new Date().toISOString().slice(0, 10),
        subscribersCount: isKnownDisinfo ? 42500 : 1200,
        score: isKnownDisinfo ? 82 : 18,
        riskBand: isKnownDisinfo ? 'high' : 'low',
        primaryNarrative: isKnownDisinfo
          ? 'Energy blackmail / Gas cut-off hysteria'
          : 'Other / not disinformation',
        clustersJoinedCount: isKnownDisinfo ? 9 : 0,
        sparkline: isKnownDisinfo
          ? [45, 60, 72, 75, 80, 84, 82]
          : [12, 14, 15, 15, 14, 15, 18],
        whyExplanation: isKnownDisinfo
          ? 'Synchronised broadcast detected within 6 minutes of lead channel post across 8 related regional outlets.'
          : 'Newly added channel; waiting for initial cluster and coordination analysis.',
      };

      if (isClean) {
        this.userWatchlistStore = [newEntry, ...this.userWatchlistStore];
      } else {
        this.watchlistStore = [newEntry, ...this.watchlistStore];
      }
      return Promise.resolve(newEntry);
    }

    return this.client.post<AddWatchlistChannelInputDto, WatchlistChannelDto>(
      '/watchlist',
      input,
    );
  }

  async toggleWatchlistStatus(channelId: string): Promise<WatchlistChannelDto> {
    if (isMockMode()) {
      const isClean = authService.isCleanProfile();
      const targetStore = isClean ? this.userWatchlistStore : this.watchlistStore;
      const index = targetStore.findIndex((c) => c.id === channelId);
      if (index === -1) {
        return Promise.reject(new Error('Channel not found on watch list.'));
      }
      const current = targetStore[index];
      const updated: WatchlistChannelDto = {
        ...current,
        status: current.status === 'active' ? 'paused' : 'active',
      };
      targetStore[index] = updated;
      return Promise.resolve(updated);
    }
    return this.client.post<Record<string, never>, WatchlistChannelDto>(
      `/watchlist/${channelId}/toggle`,
      {},
    );
  }

  async removeWatchlistChannel(channelId: string): Promise<void> {
    if (isMockMode()) {
      const isClean = authService.isCleanProfile();
      if (isClean) {
        this.userWatchlistStore = this.userWatchlistStore.filter((c) => c.id !== channelId);
      } else {
        this.watchlistStore = this.watchlistStore.filter((c) => c.id !== channelId);
      }
      return Promise.resolve();
    }
    await this.client.post<Record<string, never>, unknown>(
      `/watchlist/${channelId}/remove`,
      {},
    );
  }
}

export const channelService: IChannelService = new ChannelService();
