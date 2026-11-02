export type ExportFormat = 'csv' | 'json';
export type ExportScope = 'clusters' | 'channels';

export interface ExportQuotaDto {
  accountTier: 'new_account' | 'verified_researcher';
  maxRowsPerExport: number;
  dailyExportsLimit: number;
  dailyExportsUsed: number;
}

export interface ExportReceiptDto {
  fileName: string;
  format: ExportFormat;
  scope: ExportScope;
  rowsExported: number;
  generatedAt: string;
}

