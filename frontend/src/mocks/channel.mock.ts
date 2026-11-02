import type { ChannelDetailDto } from '../dtos/channel.dto';

export const MOCK_CHANNEL_DETAILS: Readonly<Record<string, ChannelDetailDto>> = {
  'ch-moldova-pulse': {
    id: 'ch-moldova-pulse',
    handle: '@moldova_news_pulse',
    title: 'Moldova News Pulse 24/7',
    language: 'RU',
    subscribersCount: 48200,
    status: 'active',
    addedAt: '2026-09-01',
    addedBy: 'elena.botnari',
    score: 91,
    riskBand: 'high',
    scoreHistory: [
      { dateLabel: 'Mon', score: 62 },
      { dateLabel: 'Tue', score: 68 },
      { dateLabel: 'Wed', score: 74 },
      { dateLabel: 'Thu', score: 79 },
      { dateLabel: 'Fri', score: 85 },
      { dateLabel: 'Sat', score: 88 },
      { dateLabel: 'Sun', score: 91 },
    ],
    explanation: {
      summary:
        'Flagged due to high cluster participation (24 multi-channel clusters in 7 days) and rapid copy-posting within a median 110 seconds of @gagauzia_voice_md.',
      parameterVersion: 'v3',
      participatingClustersCount: 24,
      coMovingChannels: ['@gagauzia_voice_md', '@chisinau_insider_ro', '@balti_pravda'],
      medianCopyDelaySeconds: 110,
      dominantNarrativeCategory: 'Sanctions, energy prices and economy fear',
      breakdown: {
        clusterShareScore: 34,
        copyDelayScore: 26,
        pairRepetitionScore: 19,
        narrativeWeightScore: 12,
        dominantFactor: 'Cluster Share (37% of channel posts belong to multi-channel clusters)',
      },
    },
    coMovingChannels: [
      {
        channelId: 'ch-gagauzia-voice',
        handle: '@gagauzia_voice_md',
        title: 'Голос Гагаузии • Инфо',
        sharedClustersCount: 19,
        medianTimeDiffSeconds: 110,
        averageSimilarity: 0.95,
      },
      {
        channelId: 'ch-chisinau-radar',
        handle: '@chisinau_insider_ro',
        title: 'Chișinău Insider • Știri',
        sharedClustersCount: 14,
        medianTimeDiffSeconds: 245,
        averageSimilarity: 0.91,
      },
      {
        channelId: 'ch-balti-pravda',
        handle: '@balti_pravda',
        title: 'Бельцы Правда',
        sharedClustersCount: 11,
        medianTimeDiffSeconds: 380,
        averageSimilarity: 0.92,
      },
    ],
    joinedClusters: [
      {
        clusterId: 'cl-energy-winter-01',
        headlineSummary: 'Same message posted by 5 channels in 8 minutes',
        narrativeCategory: 'Sanctions, energy prices and economy fear',
        postedAt: '2026-11-02 13:14:05',
        delaySeconds: 0,
        similarityScore: 1.0,
      },
      {
        clusterId: 'cl-elections-ballot-02',
        headlineSummary: 'Same message posted by 4 channels in 11 minutes',
        narrativeCategory: 'Moldova government and elections delegitimisation',
        postedAt: '2026-11-02 11:42:00',
        delaySeconds: 110,
        similarityScore: 0.97,
      },
      {
        clusterId: 'cl-gagauzia-autonomy-03',
        headlineSummary: 'Same message posted by 3 channels in 5 minutes',
        narrativeCategory: 'Transnistria / Gagauzia and separatism',
        postedAt: '2026-11-02 09:07:30',
        delaySeconds: 138,
        similarityScore: 1.0,
      },
    ],
  },
};

export const DEFAULT_MOCK_CHANNEL_DETAIL: ChannelDetailDto =
  MOCK_CHANNEL_DETAILS['ch-moldova-pulse'];
