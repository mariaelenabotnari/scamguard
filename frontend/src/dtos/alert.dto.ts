export type AlertSeverity = 'low' | 'medium' | 'high';
export type AlertStatus = 'new' | 'seen' | 'dismissed';

export interface AlertItemDto {
  id: string;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  summary: string;
  triggeredAt: string;
  evidencePath: string;
  narrativeCategory: string;
  parameterVersion: string;
}

