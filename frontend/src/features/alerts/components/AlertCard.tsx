import { Link } from 'react-router-dom';
import { Badge, Button, Card, Icon } from '../../../components/ui';
import type { AlertItemDto } from '../../../dtos/alert.dto';

export interface AlertCardProps {
  alert: AlertItemDto;
  onDismiss: (id: string) => void;
}

export function AlertCard({ alert, onDismiss }: AlertCardProps) {
  return (
    <Card className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant={alert.severity}
            icon={
              alert.severity === 'high'
                ? 'triangle-exclamation'
                : alert.severity === 'medium'
                  ? 'clock'
                  : 'circle-info'
            }
          >
            {alert.severity.toUpperCase()} SEVERITY
          </Badge>
          <Badge variant="brand" icon="layer-group">
            {alert.narrativeCategory}
          </Badge>
          <span className="inline-flex items-center gap-1 text-xs font-medium text-ink-muted">
            <Icon name="clock" className="text-[10px]" />
            <span>{alert.triggeredAt}</span>
          </span>
        </div>

        <h2 className="text-base font-extrabold text-ink-primary">{alert.title}</h2>
        <p className="text-xs text-ink-secondary">{alert.summary}</p>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <Link to={alert.evidencePath}>
          <Button variant="primary" size="sm" rightIcon="arrow-right">
            Open Evidence
          </Button>
        </Link>
        <Button
          variant="ghost"
          size="sm"
          leftIcon="xmark"
          aria-label={`Dismiss alert ${alert.title}`}
          onClick={() => onDismiss(alert.id)}
        >
          Dismiss
        </Button>
      </div>
    </Card>
  );
}

