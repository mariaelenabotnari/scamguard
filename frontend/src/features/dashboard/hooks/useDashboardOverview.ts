import { useCallback, useEffect, useState } from 'react';
import type { DashboardOverviewDto } from '../../../dtos/dashboard.dto';
import type { TimeRangeOption } from '../../../dtos/layout.dto';
import {
  dashboardService,
  type IDashboardService,
} from '../../../services/dashboard.service';

export interface UseDashboardOverviewResult {
  data: DashboardOverviewDto | null;
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

export function useDashboardOverview(
  range: TimeRangeOption,
  service: IDashboardService = dashboardService,
): UseDashboardOverviewResult {
  const [data, setData] = useState<DashboardOverviewDto | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    service
      .getOverview(range)
      .then((response) => {
        if (isMounted) {
          setData(response);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const message =
            err instanceof Error ? err.message : 'Failed to load dashboard overview.';
          setError(message);
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [range, service]);

  useEffect(() => {
    const cleanup = load();
    return cleanup;
  }, [load]);

  return {
    data,
    isLoading,
    error,
    reload: load,
  };
}
