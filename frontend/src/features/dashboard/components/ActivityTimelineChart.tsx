import { useEffect, useState } from 'react';
import { Card, CardHeader, EmptyState, Tabs } from '../../../components/ui';
import type { ActivityTimelineDto, TimelinePointDto } from '../../../dtos/dashboard.dto';
import type { TimeRangeOption } from '../../../dtos/layout.dto';

export interface ActivityTimelineChartProps {
  timeline: ActivityTimelineDto;
  selectedRange: TimeRangeOption;
  onRangeChange: (range: TimeRangeOption) => void;
}

const RANGE_TABS: readonly { value: TimeRangeOption; label: string }[] = [
  { value: '24h', label: '24h' },
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
];

interface PlottedPoint {
  point: TimelinePointDto;
  x: number;
  y: number;
  percentX: number;
  percentY: number;
}

function buildSmoothSplinePath(coords: readonly { x: number; y: number }[]): string {
  if (coords.length === 0) return '';
  if (coords.length === 1) return `M ${coords[0].x} ${coords[0].y}`;

  let path = `M ${coords[0].x} ${coords[0].y}`;
  for (let i = 0; i < coords.length - 1; i++) {
    const current = coords[i];
    const next = coords[i + 1];
    const controlX1 = current.x + (next.x - current.x) * 0.45;
    const controlY1 = current.y;
    const controlX2 = current.x + (next.x - current.x) * 0.55;
    const controlY2 = next.y;
    path += ` C ${controlX1.toFixed(1)} ${controlY1.toFixed(1)}, ${controlX2.toFixed(1)} ${controlY2.toFixed(1)}, ${next.x.toFixed(1)} ${next.y.toFixed(1)}`;
  }
  return path;
}

export function ActivityTimelineChart({
  timeline,
  selectedRange,
  onRangeChange,
}: ActivityTimelineChartProps) {
  const defaultPoint =
    timeline.points.find((p) => p.isHighlighted) ?? timeline.points[1] ?? timeline.points[0];
  const [selectedPointId, setSelectedPointId] = useState<string | undefined>(defaultPoint?.id);

  useEffect(() => {
    const highlighted =
      timeline.points.find((p) => p.isHighlighted) ?? timeline.points[1] ?? timeline.points[0];
    setSelectedPointId(highlighted?.id);
  }, [timeline]);

  if (timeline.points.length === 0) {
    return (
      <EmptyState
        icon="chart-line"
        title="No Activity Timeline Data"
        description="No message volume or cluster activity points were recorded for this interval."
      />
    );
  }

  const svgWidth = 680;
  const svgHeight = 220;
  const padX = 36;
  const topAnchorY = 18;
  const plotTopY = 54;
  const plotBottomY = 188;
  const usableWidth = svgWidth - padX * 2;
  const usableHeight = plotBottomY - plotTopY;

  const plotted: readonly PlottedPoint[] = timeline.points.map((point, index) => {
    const ratioX =
      timeline.points.length > 1 ? index / (timeline.points.length - 1) : 0.5;
    const x = padX + ratioX * usableWidth;
    const clampedY = Math.min(0.95, Math.max(0.08, point.normalizedY));
    const y = plotBottomY - clampedY * usableHeight;
    return {
      point,
      x,
      y,
      percentX: (x / svgWidth) * 100,
      percentY: (y / svgHeight) * 100,
    };
  });

  const activePlotted =
    plotted.find((p) => p.point.id === selectedPointId) ?? plotted[1] ?? plotted[0];

  const splinePath = buildSmoothSplinePath(plotted);
  const areaPath = `${splinePath} L ${plotted[plotted.length - 1].x.toFixed(1)} ${plotBottomY} L ${plotted[0].x.toFixed(1)} ${plotBottomY} Z`;

  return (
    <Card tone="chart" className="flex flex-1 flex-col justify-between">
      <CardHeader
        title={timeline.title}
        subtitle={timeline.subtitle}
        action={
          <Tabs
            ariaLabel="Timeline range switcher"
            items={RANGE_TABS}
            value={selectedRange}
            onChange={onRangeChange}
          />
        }
      />

      {/* Plot Canvas */}
      <div className="relative mt-2 select-none">
        {/* Floating Callout Box matching the reference PNG */}
        {activePlotted ? (
          <div
            data-testid="timeline-callout"
            style={{
              left: `${Math.min(82, Math.max(18, activePlotted.percentX))}%`,
              top: `${Math.max(8, activePlotted.percentY - 30)}%`,
            }}
            className="pointer-events-none absolute z-10 -translate-x-1/2 rounded-2xl bg-surface-tooltip/95 px-4 py-2.5 text-center shadow-pill backdrop-blur-xs transition-all duration-200"
          >
            <p className="text-[10px] font-medium text-ink-secondary">
              {activePlotted.point.dateLabel}
            </p>
            <p className="mt-0.5 text-sm font-extrabold tracking-tight text-ink-primary">
              {activePlotted.point.formattedHeadline}
            </p>
            <p className="text-[10px] font-semibold text-brand-700">
              {activePlotted.point.flaggedClustersCount} flagged clusters
            </p>
          </div>
        ) : null}

        <svg
          role="img"
          aria-label="Coordinated activity timeline chart"
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="h-56 w-full overflow-visible"
        >
          <defs>
            <linearGradient id="scamguardSplineFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6C72C9" stopOpacity="0.22" />
              <stop offset="100%" stopColor="#6C72C9" stopOpacity="0.0" />
            </linearGradient>
            <filter id="scamguardLineShadow" x="-10%" y="-10%" width="120%" height="140%">
              <feDropShadow dx="0" dy="8" stdDeviation="6" floodColor="#474B9E" floodOpacity="0.22" />
            </filter>
          </defs>

          {/* Vertical Guide Lines & Top Anchor Nodes */}
          {plotted.map(({ point, x }) => (
            <g key={`guide-${point.id}`}>
              <line
                x1={x}
                y1={topAnchorY + 8}
                x2={x}
                y2={plotBottomY + 6}
                stroke="#CFD5EE"
                strokeWidth="1.25"
              />
              <circle cx={x} cy={topAnchorY} r="7.5" fill="#CFD5EE" />
              <circle cx={x} cy={topAnchorY} r="3" fill="#474B9E" />
            </g>
          ))}

          {/* Area Gradient under Spline */}
          <path d={areaPath} fill="url(#scamguardSplineFill)" />

          {/* Smooth Cubic Spline Wave */}
          <path
            d={splinePath}
            fill="none"
            stroke="#474B9E"
            strokeWidth="2.5"
            strokeLinecap="round"
            filter="url(#scamguardLineShadow)"
          />

          {/* Interactive Data Nodes along the Curve */}
          {plotted.map(({ point, x, y }) => {
            const isSelected = point.id === activePlotted?.point.id;
            return (
              <g
                key={`node-${point.id}`}
                role="button"
                tabIndex={0}
                aria-label={`${point.axisLabel}: ${point.formattedHeadline}, ${point.flaggedClustersCount} flagged clusters`}
                onClick={() => setSelectedPointId(point.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setSelectedPointId(point.id);
                  }
                }}
                className="cursor-pointer focus:outline-none"
              >
                <circle
                  cx={x}
                  cy={y}
                  r={isSelected ? '8' : '5.5'}
                  fill="#CFD5EE"
                  fillOpacity={isSelected ? '0.95' : '0.6'}
                />
                <circle
                  cx={x}
                  cy={y}
                  r={isSelected ? '4' : '3'}
                  fill="#474B9E"
                />
              </g>
            );
          })}
        </svg>

        {/* Bottom X-Axis Labels */}
        <div
          style={{ paddingLeft: `${(padX / svgWidth) * 100}%`, paddingRight: `${(padX / svgWidth) * 100}%` }}
          className="mt-1 flex items-center justify-between text-[11px] font-medium text-ink-muted"
        >
          {timeline.points.map((point) => {
            const isSelected = point.id === activePlotted?.point.id;
            return (
              <button
                key={`axis-${point.id}`}
                type="button"
                onClick={() => setSelectedPointId(point.id)}
                className={`rounded px-1.5 py-0.5 transition-colors ${
                  isSelected
                    ? 'font-bold text-ink-primary'
                    : 'text-ink-muted hover:text-ink-primary'
                }`}
              >
                {point.axisLabel}
              </button>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

