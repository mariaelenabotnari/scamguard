import type { NarrativeCountItemDto } from '../../../dtos/dashboard.dto';
import { Card, CardHeader } from '../../../components/ui';

export interface NarrativeDistributionChartProps {
  narratives?: readonly NarrativeCountItemDto[];
}

export function NarrativeDistributionChart({
  narratives = [],
}: NarrativeDistributionChartProps) {
  return (
    <Card tone="default" className="flex flex-col justify-between p-5">
      <div>
        <CardHeader
          title="Narrative Distribution"
          subtitle="Clusters categorized by primary disinformation narrative"
        />

        <div className="mt-4 space-y-3.5">
          {narratives.map((item) => (
            <div key={item.category} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="truncate font-semibold text-ink-primary max-w-[260px]">
                  {item.category}
                </span>
                <span className="shrink-0 text-[11px] font-bold text-ink-secondary">
                  {item.clustersCount} clusters ({item.percentage}%)
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-brand-100/60">
                <div
                  style={{ width: `${Math.min(100, Math.max(4, item.percentage))}%` }}
                  className="h-full rounded-full bg-brand-600 transition-all duration-300"
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

