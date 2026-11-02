import type { ChannelDetailDto } from '../dtos/channel.dto';
import { httpClient, isMockMode, type IHttpClient } from '../lib/api/http-client';
import {
  DEFAULT_MOCK_CHANNEL_DETAIL,
  MOCK_CHANNEL_DETAILS,
} from '../mocks/channel.mock';

export interface IChannelService {
  getChannelDetail(channelId: string): Promise<ChannelDetailDto>;
}

export class ChannelService implements IChannelService {
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
}

export const channelService: IChannelService = new ChannelService();
