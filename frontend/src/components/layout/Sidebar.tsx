import { NavLink } from 'react-router-dom';
import type { NavItemDto, SidebarPulseBarDto } from '../../dtos/layout.dto';
import { Icon } from '../ui';

export interface SidebarProps {
  items: readonly NavItemDto[];
  pulseBars: readonly SidebarPulseBarDto[];
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export function Sidebar({
  items,
  pulseBars,
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onCloseMobile,
}: SidebarProps) {
  const sidebarContent = (
    <aside
      aria-label="Primary Sidebar"
      className={`relative flex h-full flex-col justify-between bg-surface-sidebar py-7 transition-all duration-200 ${
        isCollapsed ? 'w-20 px-3' : 'w-60 px-6'
      }`}
    >
      {/* Edge Collapse Toggle Button (Desktop) */}
      <button
        type="button"
        onClick={onToggleCollapse}
        aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        className="absolute -right-3.5 top-1/2 z-20 hidden h-7 w-7 -translate-y-1/2 items-center justify-center rounded-full border border-brand-100 bg-surface-card text-ink-primary shadow-pill transition-colors hover:bg-surface-banner lg:inline-flex"
      >
        <Icon name={isCollapsed ? 'chevron-right' : 'chevron-left'} className="text-[10px]" />
      </button>

      {/* Top Brand Emblem & Navigation */}
      <div className="space-y-9">
        <div className="flex flex-col items-center text-center">
          <div
            aria-hidden="true"
            className="flex h-11 w-14 items-center justify-center"
          >
            <svg
              viewBox="0 0 64 44"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="h-9 w-12"
            >
              <path
                d="M6 38L20 6L30 28L23 38H6Z"
                fill="#2D317A"
              />
              <path
                d="M25 38L39 6L58 38H45L39 24L32 38H25Z"
                fill="#474B9E"
              />
              <path
                d="M17 26L23 14L29 26H17Z"
                fill="#6C72C9"
              />
            </svg>
          </div>
          {!isCollapsed ? (
            <span className="mt-1 text-xs font-bold tracking-tight text-ink-primary">
              Scamguard
            </span>
          ) : null}
        </div>

        {/* Navigation Links */}
        <nav aria-label="Main Navigation" className="space-y-1.5">
          {items.map((item) => (
            <NavLink
              key={item.id}
              to={item.path}
              end={item.path === '/'}
              onClick={onCloseMobile}
              title={isCollapsed ? item.label : undefined}
              className={({ isActive }) =>
                `group flex items-center rounded-badge py-2.5 text-xs transition-colors ${
                  isCollapsed ? 'justify-center px-2' : 'gap-4 px-3'
                } ${
                  isActive
                    ? 'bg-surface-banner/70 font-bold text-ink-primary'
                    : 'font-medium text-ink-muted hover:bg-surface-muted hover:text-ink-primary'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={`inline-flex h-5 w-5 shrink-0 items-center justify-center ${
                      isActive
                        ? 'text-brand-700'
                        : 'text-brand-600/80 group-hover:text-brand-700'
                    }`}
                  >
                    <Icon name={item.icon} />
                  </span>
                  {!isCollapsed ? <span className="truncate">{item.label}</span> : null}
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Bottom "Statics" Activity Pulse Card */}
      {!isCollapsed ? (
        <div className="mt-8 rounded-card bg-surface-muted p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold text-ink-primary">Statics</span>
            <button
              type="button"
              aria-label="Statics options"
              className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-surface-card text-ink-muted shadow-xs hover:text-ink-primary"
            >
              <Icon name="ellipsis" className="text-[10px]" />
            </button>
          </div>

          <div
            aria-label="Collection pulse bars"
            className="mt-5 flex h-28 items-end justify-between gap-2 px-1"
          >
            {pulseBars.map((bar) => (
              <div
                key={bar.id}
                className="relative flex h-full flex-1 flex-col items-center justify-end"
              >
                {bar.tag ? (
                  <span className="mb-1.5 text-[10px] font-semibold text-ink-primary">
                    {bar.tag}
                  </span>
                ) : null}
                <div className="relative flex h-20 w-full items-end justify-center">
                  <div className="h-full w-[2px] rounded-full bg-brand-200/70" />
                  <div
                    style={{ height: `${bar.heightPercent}%` }}
                    className={`absolute bottom-0 w-1.5 rounded-full transition-all ${
                      bar.isHighlighted ? 'bg-brand-800' : 'bg-brand-400'
                    }`}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </aside>
  );

  return (
    <>
      {/* Desktop / Tablet Persistent Column */}
      <div className="hidden shrink-0 lg:block">{sidebarContent}</div>

      {/* Mobile Drawer Overlay */}
      {isMobileOpen ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Mobile navigation menu"
          className="fixed inset-0 z-50 flex lg:hidden"
        >
          <div
            className="fixed inset-0 bg-brand-900/40 backdrop-blur-xs"
            onClick={onCloseMobile}
          />
          <div className="relative z-10 flex h-full">
            {sidebarContent}
            <button
              type="button"
              onClick={onCloseMobile}
              aria-label="Close navigation drawer"
              className="m-3 inline-flex h-9 w-9 items-center justify-center rounded-full bg-surface-card text-ink-primary shadow-pill"
            >
              <Icon name="xmark" />
            </button>
          </div>
        </div>
      ) : null}
    </>
  );
}
