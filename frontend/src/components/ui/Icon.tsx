import type { IconDefinition, SizeProp } from '@fortawesome/fontawesome-svg-core';
import { faTelegram } from '@fortawesome/free-brands-svg-icons';
import {
  faArrowDown,
  faArrowRight,
  faArrowTrendDown,
  faArrowTrendUp,
  faArrowUp,
  faBars,
  faBarsStaggered,
  faBell,
  faBriefcase,
  faCalendarDays,
  faChartLine,
  faChartPie,
  faCheck,
  faCircleCheck,
  faCircleExclamation,
  faCircleInfo,
  faCircleNodes,
  faCirclePlay,
  faClock,
  faChevronDown,
  faChevronLeft,
  faChevronRight,
  faChevronUp,
  faDownload,
  faEllipsis,
  faEnvelope,
  faEye,
  faFileArrowDown,
  faFilter,
  faGaugeHigh,
  faGear,
  faHandPointer,
  faLayerGroup,
  faLock,
  faMagnifyingGlass,
  faPause,
  faPlay,
  faPlus,
  faRightFromBracket,
  faRotateRight,
  faSatelliteDish,
  faShareNodes,
  faShieldHalved,
  faSliders,
  faSpinner,
  faTrash,
  faTriangleExclamation,
  faUser,
  faUserShield,
  faUsers,
  faXmark,
} from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

export const ICON_REGISTRY = {
  'arrow-down': faArrowDown,
  'arrow-right': faArrowRight,
  'arrow-trend-down': faArrowTrendDown,
  'arrow-trend-up': faArrowTrendUp,
  'arrow-up': faArrowUp,
  bars: faBars,
  'bars-staggered': faBarsStaggered,
  bell: faBell,
  briefcase: faBriefcase,
  calendar: faCalendarDays,
  'chart-line': faChartLine,
  'chart-pie': faChartPie,
  check: faCheck,
  'chevron-down': faChevronDown,
  'chevron-left': faChevronLeft,
  'chevron-right': faChevronRight,
  'chevron-up': faChevronUp,
  'circle-check': faCircleCheck,
  'circle-exclamation': faCircleExclamation,
  'circle-info': faCircleInfo,
  'circle-nodes': faCircleNodes,
  'circle-play': faCirclePlay,
  clock: faClock,
  download: faDownload,
  ellipsis: faEllipsis,
  envelope: faEnvelope,
  eye: faEye,
  'file-arrow-down': faFileArrowDown,
  filter: faFilter,
  'gauge-high': faGaugeHigh,
  gear: faGear,
  'hand-pointer': faHandPointer,
  'layer-group': faLayerGroup,
  lock: faLock,
  'magnifying-glass': faMagnifyingGlass,
  pause: faPause,
  play: faPlay,
  plus: faPlus,
  'right-from-bracket': faRightFromBracket,
  'rotate-right': faRotateRight,
  'satellite-dish': faSatelliteDish,
  'share-nodes': faShareNodes,
  'shield-halved': faShieldHalved,
  sliders: faSliders,
  spinner: faSpinner,
  telegram: faTelegram,
  trash: faTrash,
  'triangle-exclamation': faTriangleExclamation,
  user: faUser,
  'user-shield': faUserShield,
  users: faUsers,
  xmark: faXmark,
} as const satisfies Record<string, IconDefinition>;

export type IconName = keyof typeof ICON_REGISTRY;

export interface IconProps {
  name: IconName;
  size?: SizeProp;
  className?: string;
  spin?: boolean;
  title?: string;
}

export function Icon({ name, size, className = '', spin = false, title }: IconProps) {
  const iconDefinition = ICON_REGISTRY[name];
  return (
    <FontAwesomeIcon
      icon={iconDefinition}
      size={size}
      className={className}
      spin={spin}
      title={title}
      aria-hidden={title ? undefined : true}
    />
  );
}
