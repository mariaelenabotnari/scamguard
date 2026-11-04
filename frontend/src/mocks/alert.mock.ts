import type { AlertItemDto } from '../dtos/alert.dto';

export const MOCK_ALERTS: readonly AlertItemDto[] = [
  {
    id: 'al-01',
    severity: 'high',
    status: 'new',
    title: 'Rapid 5-Channel Burst on Energy Tariffs',
    summary:
      'Cluster cl-energy-winter-01 reached 5 channels within 8 minutes (93% semantic similarity).',
    triggeredAt: '2026-11-02 13:22',
    evidencePath: '/clusters/cl-energy-winter-01',
    narrativeCategory: 'Sanctions, energy prices and economy fear',
    parameterVersion: 'v3',
  },
  {
    id: 'al-02',
    severity: 'high',
    status: 'new',
    title: 'Channel Risk Threshold Crossed: @moldova_news_pulse (91/100)',
    summary:
      '@moldova_news_pulse crossed the High-Risk threshold (≥ 75) after joining 24 coordinated clusters.',
    triggeredAt: '2026-11-02 12:45',
    evidencePath: '/channels/ch-moldova-pulse',
    narrativeCategory: 'Sanctions, energy prices and economy fear',
    parameterVersion: 'v3',
  },
  {
    id: 'al-03',
    severity: 'medium',
    status: 'seen',
    title: 'Overseas Ballot Narrative Spike (4 Channels)',
    summary:
      'Near-duplicate MinHash LSH match detected across 4 channels within 11 minutes.',
    triggeredAt: '2026-11-02 11:51',
    evidencePath: '/clusters/cl-elections-ballot-02',
    narrativeCategory: 'Moldova government and elections delegitimisation',
    parameterVersion: 'v3',
  },
  {
    id: 'al-04',
    severity: 'low',
    status: 'seen',
    title: 'Source Post Deleted After Cluster Propagation',
    summary:
      'Original post in cl-gagauzia-autonomy-03 was deleted at source; raw text purged per data retention policy.',
    triggeredAt: '2026-11-02 09:30',
    evidencePath: '/clusters/cl-gagauzia-autonomy-03',
    narrativeCategory: 'Transnistria / Gagauzia and separatism',
    parameterVersion: 'v3',
  },
];

