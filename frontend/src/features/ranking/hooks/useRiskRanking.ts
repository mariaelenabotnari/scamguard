import { useCallback, useEffect, useState } from 'react';
import type { RankedChannelDto, RiskBand } from '../../../dtos/ranking.dto';
import {
  rankingService,
  type IRankingService,
} from '../../../services/ranking.service';

export interface UseRiskRankingResult {
  channels: readonly RankedChannelDto[];
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

export function useRiskRanking(
  riskBand: RiskBand | 'all',
  query: string,
  service: IRankingService = rankingService,
): UseRiskRankingResult {
  const [channels, setChannels] = useState<readonly RankedChannelDto[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    service
      .getRankedChannels({ riskBand, query })
      .then((result) => {
        if (isMounted) {
          setChannels(result);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const message =
            err instanceof Error ? err.message : 'Failed to load channel risk ranking.';
          setError(message);
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [riskBand, query, service]);

  useEffect(() => {
    const cleanup = load();
    return cleanup;
  }, [load]);

  return {
    channels,
    isLoading,
    error,
    reload: load,
  };
}

