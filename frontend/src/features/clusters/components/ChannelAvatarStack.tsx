import { Link } from 'react-router-dom';
import { Tooltip } from '../../../components/ui';
import type { ClusterChannelParticipantDto } from '../../../dtos/cluster.dto';

export interface ChannelAvatarStackProps {
  participants: readonly ClusterChannelParticipantDto[];
  maxVisible?: number;
}

const AVATAR_BG_CLASSES: readonly string[] = [
  'bg-brand-700 text-white',
  'bg-brand-500 text-white',
  'bg-status-infoText text-white',
  'bg-status-warningText text-white',
  'bg-brand-900 text-white',
];

export function ChannelAvatarStack({
  participants,
  maxVisible = 4,
}: ChannelAvatarStackProps) {
  const visible = participants.slice(0, maxVisible);
  const overflowCount = Math.max(0, participants.length - visible.length);

  return (
    <div className="flex items-center">
      <div className="flex -space-x-2">
        {visible.map((participant, index) => (
          <Tooltip
            key={participant.channelId}
            content={`${participant.handle} • +${participant.delaySeconds}s (${Math.round(participant.similarityScore * 100)}% match)`}
          >
            <Link
              to={`/channels/${participant.channelId}`}
              aria-label={`Channel ${participant.handle}`}
              className={`inline-flex h-8 w-8 items-center justify-center rounded-full border-2 border-surface-card text-[10px] font-bold shadow-xs transition-transform hover:z-10 hover:scale-105 ${
                AVATAR_BG_CLASSES[index % AVATAR_BG_CLASSES.length]
              }`}
            >
              {participant.initials}
            </Link>
          </Tooltip>
        ))}

        {overflowCount > 0 ? (
          <span
            aria-label={`${overflowCount} more channels`}
            className="inline-flex h-8 w-8 items-center justify-center rounded-full border-2 border-surface-card bg-surface-banner text-[10px] font-bold text-ink-primary"
          >
            +{overflowCount}
          </span>
        ) : null}
      </div>

      <div className="ml-3 hidden flex-wrap gap-1.5 sm:flex">
        {visible.slice(0, 3).map((participant) => (
          <Link
            key={`chip-${participant.channelId}`}
            to={`/channels/${participant.channelId}`}
            className="rounded-md bg-surface-muted px-2 py-0.5 text-[11px] font-semibold text-ink-secondary hover:bg-brand-100 hover:text-ink-primary"
          >
            {participant.handle}
          </Link>
        ))}
      </div>
    </div>
  );
}

