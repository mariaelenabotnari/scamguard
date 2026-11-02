import React, { useEffect } from 'react';
import { Icon } from './Icon';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export function Modal({ isOpen, onClose, title, subtitle, children, footer }: ModalProps) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-brand-900/40 p-4 backdrop-blur-xs"
    >
      <div className="w-full max-w-lg rounded-card bg-surface-card p-6 shadow-shell">
        <div className="flex items-start justify-between gap-4 border-b border-brand-100 pb-4">
          <div>
            <h2 id="modal-title" className="text-lg font-bold text-ink-primary">
              {title}
            </h2>
            {subtitle ? <p className="mt-0.5 text-xs text-ink-muted">{subtitle}</p> : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-surface-muted text-ink-muted transition-colors hover:bg-brand-100 hover:text-ink-primary"
          >
            <Icon name="xmark" />
          </button>
        </div>
        <div className="py-4 text-sm text-ink-secondary">{children}</div>
        {footer ? (
          <div className="flex items-center justify-end gap-2.5 border-t border-brand-100 pt-4">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  );
}
