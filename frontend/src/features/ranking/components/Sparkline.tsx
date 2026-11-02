import type { RiskBand } from '../../../dtos/ranking.dto';

export interface SparklineProps {
  values: readonly number[];
  riskBand: RiskBand;
  label?: string;
}

const STROKE_COLORS: Record<RiskBand, string> = {
  high: '#BE123C',
  medium: '#B45309',
  low: '#1E6B7B',
};

export function Sparkline({ values, riskBand, label = 'Score trend' }: SparklineProps) {
  if (values.length === 0) return null;

  const width = 96;
  const height = 28;
  const pad = 3;
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = Math.max(1, maxVal - minVal);

  const points = values.map((val, index) => {
    const x =
      values.length > 1
        ? pad + (index / (values.length - 1)) * (width - pad * 2)
        : width / 2;
    const y = height - pad - ((val - minVal) / range) * (height - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const lastPoint = points[points.length - 1]?.split(',') ?? ['0', '0'];
  const strokeColor = STROKE_COLORS[riskBand];

  return (
    <svg
      role="img"
      aria-label={label}
      viewBox={`0 0 ${width} ${height}`}
      className="h-7 w-24 overflow-visible"
    >
      <polyline
        fill="none"
        stroke={strokeColor}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points.join(' ')}
      />
      <circle
        cx={lastPoint[0]}
        cy={lastPoint[1]}
        r="2.8"
        fill={strokeColor}
      />
    </svg>
  );
}

