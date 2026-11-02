import type { DashboardOverviewDto } from '../dtos/dashboard.dto';
import type { TimeRangeOption } from '../dtos/layout.dto';
import { httpClient, isMockMode, type IHttpClient } from '../lib/api/http-client';
import { MOCK_DASHBOARD_OVERVIEW_BY_RANGE } from '../mocks/dashboard.mock';

export interface IDashboardService {
  getOverview(range: TimeRangeOption): Promise<DashboardOverviewDto>;
}

export class DashboardService implements IDashboardService {
  constructor(private readonly client: IHttpClient = httpClient) {}

  async getOverview(range: TimeRangeOption): Promise<DashboardOverviewDto> {
    if (isMockMode()) {
      return Promise.resolve(MOCK_DASHBOARD_OVERVIEW_BY_RANGE[range]);
    }
    return this.client.get<DashboardOverviewDto>(`/dashboard/overview?range=${range}`);
  }
}

export const dashboardService: IDashboardService = new DashboardService();
