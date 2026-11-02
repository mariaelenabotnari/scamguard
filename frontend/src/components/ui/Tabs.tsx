import { Icon, type IconName } from './Icon';

export interface TabItem<TValue extends string = string> {
  value: TValue;
  label: string;
  icon?: IconName;
  count?: number;
}

export interface TabsProps<TValue extends string = string> {
  items: readonly TabItem<TValue>[];
  value: TValue;
  onChange: (value: TValue) => void;
  variant?: 'pill' | 'soft';
  ariaLabel?: string;
  className?: string;
}

export function Tabs<TValue extends string = string>({
  items,
  value,
  onChange,
  variant = 'pill',
  ariaLabel = 'View switcher',
  className = '',
}: TabsProps<TValue>) {
  if (variant === 'pill') {
    return (
      <div
        role="tablist"
        aria-label={ariaLabel}
        className={`inline-flex items-center rounded-full bg-brand-700 p-1 shadow-pill ${className}`}
      >
        {items.map((item) => {
          const isActive = item.value === value;
          return (
            <button
              key={item.value}
              role="tab"
              type="button"
              aria-selected={isActive}
              onClick={() => onChange(item.value)}
              className={`inline-flex items-center gap-1.5 rounded-full px-4 py-1 text-xs font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white ${
                isActive
                  ? 'bg-surface-card text-ink-primary shadow-sm'
                  : 'text-brand-100 hover:text-white'
              }`}
            >
              {item.icon ? <Icon name={item.icon} className="text-[11px]" /> : null}
              <span>{item.label}</span>
              {typeof item.count === 'number' ? (
                <span className="ml-1 rounded-full bg-brand-100 px-1.5 py-0.2 text-[10px] text-brand-800">
                  {item.count}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={`inline-flex items-center gap-1.5 rounded-badge bg-surface-muted p-1 ${className}`}
    >
      {items.map((item) => {
        const isActive = item.value === value;
        return (
          <button
            key={item.value}
            role="tab"
            type="button"
            aria-selected={isActive}
            onClick={() => onChange(item.value)}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${
              isActive
                ? 'bg-surface-card text-ink-primary shadow-sm'
                : 'text-ink-muted hover:text-ink-primary'
            }`}
          >
            {item.icon ? <Icon name={item.icon} className="text-xs" /> : null}
            <span>{item.label}</span>
            {typeof item.count === 'number' ? (
              <span className="rounded-full bg-brand-100 px-1.5 py-0.5 text-[10px] text-brand-700">
                {item.count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
