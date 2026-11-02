import { useCallback, useEffect, useState } from 'react';
import type { ChannelDetailDto } from '../../../dtos/channel.dto';
import {
  channelService,
  type IChannelService,
} from '../../../services/channel.service';

export interface UseChannelDetailResult {
  channel: ChannelDetailDto | null;
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

export function useChannelDetail(
  channelId: string,
  service: IChannelService = channelService,
): UseChannelDetailResult {
  const [channel, setChannel] = useState<ChannelDetailDto | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    service
      .getChannelDetail(channelId)
      .then((result) => {
        if (isMounted) {
          setChannel(result);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const message =
            err instanceof Error ? err.message : 'Failed to load channel profile.';
          setError(message);
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [channelId, service]);

  useEffect(() => {
    const cleanup = load();
    return cleanup;
  }, [load]);

  return {
    channel,
    isLoading,
    error,
    reload: load,
  };
}
