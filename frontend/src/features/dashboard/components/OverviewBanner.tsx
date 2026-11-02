import type { DashboardBannerDto } from '../../../dtos/dashboard.dto';
import { Card } from '../../../components/ui';

export interface OverviewBannerProps {
  banner: DashboardBannerDto;
}

export function OverviewBanner({ banner }: OverviewBannerProps) {
  return (
    <Card
      tone="banner"
      padding="none"
      className="relative flex min-h-[136px] flex-col justify-center overflow-hidden px-7 py-6 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="z-10 max-w-md space-y-1.5">
        <h1 className="text-2xl font-extrabold tracking-tight text-brand-800 sm:text-[26px]">
          {banner.greetingTitle}
        </h1>
        <p className="text-xs font-medium text-ink-muted">{banner.subtitle}</p>
      </div>

      {/* Decorative Indigo Vector Illustration matching reference banner */}
      <div
        aria-hidden="true"
        className="pointer-events-none mt-4 flex items-end justify-end sm:absolute sm:bottom-0 sm:right-6 sm:mt-0"
      >
        <svg
          width="196"
          height="122"
          viewBox="0 0 196 122"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="h-28 w-auto"
        >
          {/* Soft periwinkle sun/radar circle */}
          <circle cx="118" cy="40" r="24" fill="#6C72C9" fillOpacity="0.85" />
          {/* Cloud wisps */}
          <path
            d="M28 54H48C50.2 54 52 52.2 52 50C52 47.8 50.2 46 48 46H45C43.5 41.5 39 39 34 40.5C30.5 41.5 28 45 28 49V54Z"
            fill="#AAB2E0"
            fillOpacity="0.65"
          />
          <path
            d="M150 38H166C167.7 38 169 36.7 169 35C169 33.3 167.7 32 166 32H163.5C162.3 28.8 159 27 155.5 28C152.5 28.8 150 31.5 150 34.8V38Z"
            fill="#AAB2E0"
            fillOpacity="0.65"
          />
          {/* Foreground indigo hills */}
          <path
            d="M14 122C24 96 52 88 76 102C92 78 128 76 146 98C162 92 182 100 190 122H14Z"
            fill="#474B9E"
          />
          {/* Stylized figure silhouette walking across hill */}
          <circle cx="88" cy="30" r="6.5" fill="#1E2258" />
          {/* Backpack */}
          <rect
            x="92"
            y="38"
            width="16"
            height="24"
            rx="6"
            transform="rotate(12 92 38)"
            fill="#1E2258"
          />
          {/* Torso */}
          <path d="M80 40L95 40L92 66H77L80 40Z" fill="#FFFFFF" />
          {/* Legs */}
          <path d="M79 65L71 96H78L86 68L95 96H102L91 65H79Z" fill="#1E2258" />
        </svg>
      </div>
    </Card>
  );
}
