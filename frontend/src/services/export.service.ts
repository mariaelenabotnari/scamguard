import type {
  ExportFormat,
  ExportQuotaDto,
  ExportReceiptDto,
  ExportScope,
} from '../dtos/export.dto';
import { httpClient, isMockMode, type IHttpClient } from '../lib/api/http-client';

export interface IExportService {
  getQuota(): Promise<ExportQuotaDto>;
  triggerExport(scope: ExportScope, format: ExportFormat): Promise<ExportReceiptDto>;
}

export class ExportService implements IExportService {
  private usedToday = 1;

  constructor(private readonly client: IHttpClient = httpClient) {}

  async getQuota(): Promise<ExportQuotaDto> {
    if (isMockMode()) {
      return Promise.resolve({
        accountTier: 'new_account',
        maxRowsPerExport: 250,
        dailyExportsLimit: 3,
        dailyExportsUsed: this.usedToday,
      });
    }
    return this.client.get<ExportQuotaDto>('/export/quota');
  }

  async triggerExport(
    scope: ExportScope,
    format: ExportFormat,
  ): Promise<ExportReceiptDto> {
    if (isMockMode()) {
      this.usedToday += 1;
      return Promise.resolve({
        fileName: `scamguard_${scope}_2026-11-02.${format}`,
        format,
        scope,
        rowsExported: scope === 'clusters' ? 48 : 312,
        generatedAt: '2026-11-02 14:15:00',
      });
    }
    return this.client.post<{ scope: ExportScope; format: ExportFormat }, ExportReceiptDto>(
      '/export',
      { scope, format },
    );
  }
}

export const exportService: IExportService = new ExportService();

