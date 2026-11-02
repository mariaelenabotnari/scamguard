export interface HealthStatusDto {
  status: 'ok' | 'degraded' | 'down';
  service: string;
  version: string;
}

