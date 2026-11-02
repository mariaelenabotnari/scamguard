import type { NavItemDto, ShellSummaryDto } from '../dtos/layout.dto';
import { httpClient, isMockMode, type IHttpClient } from '../lib/api/http-client';
import { MOCK_SHELL_SUMMARY, PRIMARY_NAV_ITEMS } from '../mocks/layout.mock';

export interface ILayoutService {
  getNavItems(): readonly NavItemDto[];
  getShellSummary(): Promise<ShellSummaryDto>;
}

export class LayoutService implements ILayoutService {
  constructor(private readonly client: IHttpClient = httpClient) {}

  getNavItems(): readonly NavItemDto[] {
    return PRIMARY_NAV_ITEMS;
  }

  async getShellSummary(): Promise<ShellSummaryDto> {
    if (isMockMode()) {
      return Promise.resolve(MOCK_SHELL_SUMMARY);
    }
    return this.client.get<ShellSummaryDto>('/meta/shell-summary');
  }
}

export const layoutService: ILayoutService = new LayoutService();
