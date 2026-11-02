import type { AlertItemDto, AlertSeverity } from '../dtos/alert.dto';
import { httpClient, isMockMode, type IHttpClient } from '../lib/api/http-client';
import { MOCK_ALERTS } from '../mocks/alert.mock';

export interface IAlertService {
  getAlerts(severity?: AlertSeverity | 'all'): Promise<readonly AlertItemDto[]>;
  dismissAlert(alertId: string): Promise<void>;
}

export class AlertService implements IAlertService {
  private mockStore: AlertItemDto[] = [...MOCK_ALERTS];

  constructor(private readonly client: IHttpClient = httpClient) {}

  async getAlerts(severity: AlertSeverity | 'all' = 'all'): Promise<readonly AlertItemDto[]> {
    if (isMockMode()) {
      const visible = this.mockStore.filter(
        (item) =>
          item.status !== 'dismissed' &&
          (severity === 'all' || item.severity === severity),
      );
      return Promise.resolve(visible);
    }
    const qs = severity !== 'all' ? `?severity=${severity}` : '';
    return this.client.get<readonly AlertItemDto[]>(`/alerts${qs}`);
  }

  async dismissAlert(alertId: string): Promise<void> {
    if (isMockMode()) {
      this.mockStore = this.mockStore.map((item) =>
        item.id === alertId ? { ...item, status: 'dismissed' } : item,
      );
      return Promise.resolve();
    }
    await this.client.post<{ status: string }, unknown>(`/alerts/${alertId}/dismiss`, {
      status: 'dismissed',
    });
  }
}

export const alertService: IAlertService = new AlertService();
