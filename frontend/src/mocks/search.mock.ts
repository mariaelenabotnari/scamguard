import type { SearchMessageHitDto } from '../dtos/search.dto';
import { MOCK_RANKED_CHANNELS } from './ranking.mock';

export const MOCK_SEARCH_MESSAGES: readonly SearchMessageHitDto[] = [
  {
    id: 'msg-501',
    channelId: 'ch-moldova-pulse',
    handle: '@moldova_news_pulse',
    postedAt: '2026-11-02 13:14:05',
    snippet:
      'URGENT: Tarifele la gaze și energie electrică vor fi dublate după 15 noiembrie din cauza condițiilor impuse de Bruxelles pentru împrumutul extern.',
    narrativeCategory: 'Sanctions, energy prices and economy fear',
    clusterId: 'cl-energy-winter-01',
    channelScore: 91,
    riskBand: 'high',
    explanation: MOCK_RANKED_CHANNELS[0].explanation,
  },
  {
    id: 'msg-502',
    channelId: 'ch-chisinau-radar',
    handle: '@chisinau_insider_ro',
    postedAt: '2026-11-02 13:18:12',
    snippet:
      'ALERTĂ: Tarifele la gaze și energie electrică vor fi majorate cu 100% din 15 noiembrie din cauza condițiilor impuse de Bruxelles!',
    narrativeCategory: 'Sanctions, energy prices and economy fear',
    clusterId: 'cl-energy-winter-01',
    channelScore: 78,
    riskBand: 'high',
    explanation: MOCK_RANKED_CHANNELS[2].explanation,
  },
  {
    id: 'msg-503',
    channelId: 'ch-gagauzia-voice',
    handle: '@gagauzia_voice_md',
    postedAt: '2026-11-02 11:40:10',
    snippet:
      'Сотни бюллетеней якобы уже подготовлены на зарубежных участках до открытия голосования — источники сообщают о закрытом распоряжении ЦИК.',
    narrativeCategory: 'Moldova government and elections delegitimisation',
    clusterId: 'cl-elections-ballot-02',
    channelScore: 86,
    riskBand: 'high',
    explanation: MOCK_RANKED_CHANNELS[1].explanation,
  },
];
