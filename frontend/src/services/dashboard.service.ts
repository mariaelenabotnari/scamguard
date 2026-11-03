import type { DashboardOverviewDto } from '../dtos/dashboard.dto';
import type { TimeRangeOption } from '../dtos/layout.dto';
import { httpClient, isMockMode, type IHttpClient } from '../lib/api/http-client';
import { MOCK_DASHBOARD_OVERVIEW_BY_RANGE } from '../mocks/dashboard.mock';
import { authService } from './auth.service';
import { channelService } from './channel.service';

export interface IDashboardService {
  getOverview(range: TimeRangeOption): Promise<DashboardOverviewDto>;
}

export class DashboardService implements IDashboardService {
  constructor(private readonly client: IHttpClient = httpClient) {}

  async getOverview(range: TimeRangeOption): Promise<DashboardOverviewDto> {
    if (isMockMode()) {
      if (authService.isCleanProfile()) {
        const channels = await channelService.getWatchlist();
        const channelCount = channels.length;
        const highRiskCount = channels.filter((c) => (c.score ?? 0) >= 70).length;

        return Promise.resolve({
          range,
          banner: {
            greetingTitle: 'Welcome to ChorusWatch',
            subtitle:
              channelCount === 0
                ? 'Your fresh investigation workspace is ready. Add channels to begin monitoring.'
                : `${channelCount} channels currently under active surveillance.`,
            activeChannelsCount: channelCount,
            parameterVersion: 'v1.4',
          },
          timeline: {
            title: 'Message and Cluster Activity',
            subtitle: 'Hourly volume and detected coordination groups',
            range,
            points: [],
          },
          stats: [
            {
              id: 'watched-channels',
              label: 'Channels watched',
              formattedValue: String(channelCount),
              numericValue: channelCount,
              deltaPercent: 0,
              formattedDelta: '+0',
              trendDirection: 'up',
              icon: 'tower-broadcast',
              tone: 'lavender',
              subline: channelCount === 0 ? 'No channels monitored' : `${channelCount} active`,
              targetPath: '/channels',
            },
            {
              id: 'messages-analysed',
              label: 'Messages analysed',
              formattedValue: String(channelCount * 28),
              numericValue: channelCount * 28,
              deltaPercent: 0,
              formattedDelta: '+0',
              trendDirection: 'up',
              icon: 'envelope',
              tone: 'cyan',
              subline: `in the last ${range}`,
              targetPath: '/search',
            },
            {
              id: 'clusters-found',
              label: 'Clusters detected',
              formattedValue: String(highRiskCount),
              numericValue: highRiskCount,
              deltaPercent: 0,
              formattedDelta: '+0',
              trendDirection: 'up',
              icon: 'diagram-project',
              tone: 'peach',
              subline: 'coordination groups',
              targetPath: '/clusters',
            },
            {
              id: 'alerts-pending',
              label: 'Active alerts',
              formattedValue: String(highRiskCount),
              numericValue: highRiskCount,
              deltaPercent: 0,
              formattedDelta: '+0',
              trendDirection: 'up',
              icon: 'bell',
              tone: 'rose',
              subline: 'requiring review',
              targetPath: '/alerts',
            },
          ],
          topClusters: channels
            .filter((c) => (c.score ?? 0) >= 70)
            .map((c) => ({
              id: `cl-${c.id}`,
              headline: `${channelCount} channels posted identical text in 6 minutes`,
              narrativeCategory: c.primaryNarrative || 'Coordinated messaging',
              channelsCount: channelCount,
              timeWindow: '6 min spread',
              postedAtLabel: '12m ago',
            })),
          riskiestChannels: channels.map((c) => ({
            id: c.id,
            handle: c.handle,
            title: c.title,
            score: c.score ?? 15,
            riskBand: c.riskBand ?? 'low',
            sparkline: c.sparkline ?? [15, 15, 15, 15, 15],
            primaryNarrative: c.primaryNarrative ?? 'General news',
          })),
          narrativeCounts:
            highRiskCount > 0
              ? [
                  {
                    category: 'Energy blackmail',
                    clustersCount: highRiskCount,
                    percentage: 100,
                  },
                ]
              : [],
          systemStatus: {
            lastCollectionLabel: 'Just now • Active',
            nextRunLabel: 'in 5m',
            connectionStatus: 'ok',
            analysisDelaySeconds: 4,
          },
        });
      }

      return Promise.resolve(MOCK_DASHBOARD_OVERVIEW_BY_RANGE[range]);
    }
    return this.client.get<DashboardOverviewDto>(`/dashboard/overview?range=${range}`);
  }
}

export const dashboardService: IDashboardService = new DashboardService();
