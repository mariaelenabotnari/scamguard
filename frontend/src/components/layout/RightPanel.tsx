import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type {
  AuditGaugeDto,
  CalendarDayDto,
  QuickSummaryCardDto,
  UserProfileSummaryDto,
} from '../../dtos/layout.dto';
import { Badge, Icon } from '../ui';

export interface RightPanelProps {
  user: UserProfileSummaryDto;
  quickCards: readonly QuickSummaryCardDto[];
  calendarDays: readonly CalendarDayDto[];
  audit: AuditGaugeDto;
}

export function RightPanel({ user, quickCards, calendarDays, audit }: RightPanelProps) {
  const navigate = useNavigate();
  const [selectedDay, setSelectedDay] = useState<number>(
    () => calendarDays.find((d) => d.isActive)?.dateNumber ?? 13,
  );
  const [periodVisible, setPeriodVisible] = useState(true);

  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset =
    circumference - (Math.min(100, Math.max(0, audit.primaryPercentage)) / 100) * circumference;

  return (
    <aside
      aria-label="Analyst Summary Panel"
      className="flex w-full shrink-0 flex-col justify-between gap-6 bg-surface-panel p-6 lg:w-[300px] xl:w-[315px]"
    >
      {/* Top User Profile Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3.5">
          <div
            aria-hidden="true"
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 border-white bg-brand-700 text-sm font-bold text-white shadow-pill"
          >
            {user.initials}
          </div>
          <div>
            <h2 className="text-base font-bold leading-tight text-ink-primary">{user.fullName}</h2>
            <p className="mt-0.5 text-xs font-medium text-ink-muted">{user.roleLabel}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => navigate('/admin')}
          aria-label="Open user and threshold settings"
          className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-ink-primary transition-colors hover:bg-brand-200/60"
        >
          <Icon name="bars-staggered" className="text-sm" />
        </button>
      </div>

      {/* 3 Stacked Quick-Metric Action Cards */}
      <div className="space-y-3.5">
        {quickCards.map((card) => (
          <div
            key={card.id}
            className="flex items-center justify-between rounded-card bg-surface-card px-5 py-3.5 shadow-card"
          >
            <div>
              <p className="text-[11px] font-medium text-ink-muted">{card.label}</p>
              <p className="mt-1 text-lg font-extrabold tracking-tight text-ink-primary">
                {card.value}
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate(card.targetPath)}
              aria-label={`View ${card.label}`}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-surface-muted text-ink-primary transition-colors hover:bg-brand-100"
            >
              <Icon name="chevron-right" className="text-[10px]" />
            </button>
          </div>
        ))}
      </div>

      {/* 7-Day Activity Strip */}
      <div
        role="group"
        aria-label="Weekly activity day selector"
        className="flex items-center justify-between px-1"
      >
        {calendarDays.map((day) => {
          const isSelected = day.dateNumber === selectedDay;
          return (
            <button
              key={day.dayShort}
              type="button"
              aria-pressed={isSelected}
              onClick={() => setSelectedDay(day.dateNumber)}
              className={`relative flex flex-col items-center rounded-full px-2.5 py-2.5 text-xs transition-all ${
                isSelected
                  ? 'bg-brand-700 text-white shadow-pill'
                  : 'text-ink-muted hover:bg-brand-200/50 hover:text-ink-primary'
              }`}
            >
              <span
                className={`text-[10px] font-medium ${
                  isSelected ? 'text-brand-100' : 'text-ink-muted'
                }`}
              >
                {day.dayShort}
              </span>
              <span
                className={`mt-1.5 text-xs font-bold ${
                  isSelected ? 'text-white' : 'text-ink-primary'
                }`}
              >
                {day.dateNumber}
              </span>
              {day.hasAlertDot ? (
                <span
                  aria-hidden="true"
                  className={`mt-1 h-1 w-1 rounded-full ${
                    isSelected ? 'bg-amber-300' : 'bg-amber-400'
                  }`}
                />
              ) : (
                <span aria-hidden="true" className="mt-1 h-1 w-1" />
              )}
            </button>
          );
        })}
      </div>

      {/* Audit / Radial Score Gauge Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-brand-200 pb-3">
          <h3 className="text-xs font-bold text-ink-primary">{audit.title}</h3>
          {periodVisible ? (
            <Badge variant="neutral" onDismiss={() => setPeriodVisible(false)}>
              {audit.periodLabel}
            </Badge>
          ) : null}
        </div>

        {/* Radial Donut Gauge */}
        <div className="flex items-center justify-center py-2">
          <div className="relative flex h-36 w-36 items-center justify-center">
            <svg className="h-full w-full -rotate-90" viewBox="0 0 128 128">
              <circle
                cx="64"
                cy="64"
                r={radius}
                fill="transparent"
                stroke="#CFD5EE"
                strokeWidth="8"
              />
              <circle
                cx="64"
                cy="64"
                r="47"
                fill="transparent"
                stroke="#FFFFFF"
                strokeWidth="2.5"
              />
              <circle
                cx="64"
                cy="64"
                r={radius}
                fill="transparent"
                stroke="#474B9E"
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
              <span className="text-2xl font-extrabold text-ink-primary">
                {audit.primaryPercentage}%
              </span>
              <span className="text-[11px] font-medium text-ink-muted">{audit.primaryLabel}</span>
            </div>
          </div>
        </div>

        {/* Bottom Linear Progress Bar */}
        <div className="space-y-1.5">
          <div className="flex items-baseline justify-between">
            <div>
              <p className="text-base font-extrabold text-ink-primary">
                {audit.secondaryPercentage}%
              </p>
              <p className="text-[10px] font-medium text-ink-muted">{audit.secondaryLabel}</p>
            </div>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-brand-200">
            <div
              style={{ width: `${audit.secondaryPercentage}%` }}
              className="h-full rounded-full bg-brand-700"
            />
          </div>
        </div>
      </div>
    </aside>
  );
}
