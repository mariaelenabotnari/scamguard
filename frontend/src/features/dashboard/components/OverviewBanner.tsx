import type { DashboardBannerDto } from '../../../dtos/dashboard.dto';

export interface OverviewBannerProps {
  banner: DashboardBannerDto;
}

export function OverviewBanner({ banner }: OverviewBannerProps) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary sm:text-[26px]">
          {banner.greetingTitle || 'Overview'}
        </h1>
        <p className="mt-0.5 text-xs font-medium text-ink-muted">
          {banner.subtitle ||
            'Monitor coordinated activity and narrative spread across watched Telegram channels.'}
        </p>
      </div>
    </div>
  );
}
