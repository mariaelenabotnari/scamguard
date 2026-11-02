import type { HealthStatusDto } from '../dtos/system.dto';
import { httpClient, isMockMode, type IHttpClient } from '../lib/api/http-client';

export interface ISystemService {
  getHealth(): Promise<HealthStatusDto>;
}

export class SystemService implements ISystemService {
  constructor(private readonly client: IHttpClient = httpClient) {}

  async getHealth(): Promise<HealthStatusDto> {
    if (isMockMode()) {
      return {
        status: 'ok',
        service: 'scamguard-backend',
        version: '0.1.0',
      };
    }
    return this.client.get<HealthStatusDto>('/health');
  }
}

export const systemService: ISystemService = new SystemService();

