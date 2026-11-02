import { useCallback, useEffect, useState } from 'react';
import type { AlertItemDto, AlertSeverity } from '../../../dtos/alert.dto';
import { alertService, type IAlertService } from '../../../services/alert.service';

export interface UseAlertsFeedResult {
  alerts: readonly AlertItemDto[];
  isLoading: boolean;
  error: string | null;
  dismiss: (alertId: string) => Promise<void>;
  reload: () => void;
}

export function useAlertsFeed(
  severity: AlertSeverity | 'all',
  service: IAlertService = alertService,
): UseAlertsFeedResult {
  const [alerts, setAlerts] = useState<readonly AlertItemDto[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    service
      .getAlerts(severity)
      .then((result) => {
        if (isMounted) {
          setAlerts(result);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const message = err instanceof Error ? err.message : 'Failed to load alerts feed.';
          setError(message);
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [severity, service]);

  useEffect(() => {
    const cleanup = load();
    return cleanup;
  }, [load]);

  const dismiss = async (alertId: string) => {
    await service.dismissAlert(alertId);
    setAlerts((prev) => prev.filter((item) => item.id !== alertId));
  };

  return {
    alerts,
    isLoading,
    error,
    dismiss,
    reload: load,
  };
}
