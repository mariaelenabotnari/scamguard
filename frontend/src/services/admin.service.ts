import type {
  SystemParametersDto,
  UpdateSystemParametersInputDto,
} from '../dtos/admin.dto';
import { httpClient, isMockMode, type IHttpClient } from '../lib/api/http-client';

const INITIAL_PARAMETERS: SystemParametersDto = {
  parameterVersion: 'v1.4',
  similarityThreshold: 0.82,
  timeWindowMinutes: 30,
  collectionIntervalMinutes: 5,
  minClusterChannels: 3,
  updatedAt: '2026-11-02 12:00',
  updatedBy: 'elena.botnari@scamguard.md',
};

export interface IAdminService {
  getParameters(): Promise<SystemParametersDto>;
  updateParameters(input: UpdateSystemParametersInputDto): Promise<SystemParametersDto>;
}

export class AdminService implements IAdminService {
  private currentParams: SystemParametersDto = { ...INITIAL_PARAMETERS };
  private minorVersion = 4;

  constructor(private readonly client: IHttpClient = httpClient) {}

  async getParameters(): Promise<SystemParametersDto> {
    if (isMockMode()) {
      return Promise.resolve({ ...this.currentParams });
    }
    return this.client.get<SystemParametersDto>('/admin/parameters');
  }

  async updateParameters(
    input: UpdateSystemParametersInputDto,
  ): Promise<SystemParametersDto> {
    if (
      Number.isNaN(input.collectionIntervalMinutes) ||
      input.collectionIntervalMinutes < 1 ||
      input.collectionIntervalMinutes > 10
    ) {
      return Promise.reject(
        new Error(
          'Collection interval must be between 1 and 10 minutes.',
        ),
      );
    }

    if (
      Number.isNaN(input.similarityThreshold) ||
      input.similarityThreshold < 0.5 ||
      input.similarityThreshold > 0.99
    ) {
      return Promise.reject(
        new Error('Similarity threshold must be between 0.50 and 0.99.'),
      );
    }

    if (
      Number.isNaN(input.timeWindowMinutes) ||
      input.timeWindowMinutes < 5 ||
      input.timeWindowMinutes > 180
    ) {
      return Promise.reject(
        new Error('Coordination time window must be between 5 and 180 minutes.'),
      );
    }

    if (isMockMode()) {
      this.minorVersion += 1;
      this.currentParams = {
        parameterVersion: `v1.${this.minorVersion}`,
        similarityThreshold: input.similarityThreshold,
        timeWindowMinutes: input.timeWindowMinutes,
        collectionIntervalMinutes: input.collectionIntervalMinutes,
        minClusterChannels: input.minClusterChannels,
        updatedAt: '2026-11-02 19:25',
        updatedBy: 'elena.botnari@scamguard.md',
      };
      return Promise.resolve({ ...this.currentParams });
    }

    return this.client.post<UpdateSystemParametersInputDto, SystemParametersDto>(
      '/admin/parameters',
      input,
    );
  }
}

export const adminService: IAdminService = new AdminService();

