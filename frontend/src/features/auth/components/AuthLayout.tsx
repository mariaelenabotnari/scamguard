import React from 'react';

export interface AuthLayoutProps {
  children: React.ReactNode;
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface-canvas p-4 sm:p-6 lg:p-8">
      {/* Centered Brand Emblem & Title */}
      <div className="mb-6 flex flex-col items-center text-center">
        <div aria-hidden="true" className="flex h-12 w-16 items-center justify-center">
          <svg
            viewBox="0 0 64 44"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="h-10 w-14 drop-shadow-sm"
          >
            <path d="M6 38L20 6L30 28L23 38H6Z" fill="#2D317A" />
            <path d="M25 38L39 6L58 38H45L39 24L32 38H25Z" fill="#474B9E" />
            <path d="M17 26L23 14L29 26H17Z" fill="#6C72C9" />
          </svg>
        </div>
        <span className="mt-2 text-2xl font-black tracking-tight text-ink-primary">
          ChorusWatch
        </span>
        <p className="mt-1 text-xs font-medium text-ink-muted">
          Moldova Telegram Disinformation &amp; Coordination Detection
        </p>
      </div>

      {/* Main Auth Form Container */}
      <div className="w-full max-w-md">{children}</div>

      {/* Bottom Footer Info */}
      <footer className="mt-8 text-center text-[11px] font-medium text-ink-muted">
        <p>© 2026 ChorusWatch • Independent Media Research &amp; Disinformation Forensics</p>
      </footer>
    </div>
  );
}

