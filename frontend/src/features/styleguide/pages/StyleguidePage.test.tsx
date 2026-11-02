import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppRoutes } from '../../../app/router';

describe('StyleguidePage (/styleguide)', () => {
  it('renders all design system primitives and opens evidence modal', () => {
    render(
      <MemoryRouter initialEntries={['/styleguide']}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole('heading', { name: /scamguard design system/i }),
    ).toBeInTheDocument();

    // Buttons & Badges
    expect(screen.getByRole('button', { name: /add channel/i })).toBeInTheDocument();
    expect(screen.getByText(/high risk \(89\)/i)).toBeInTheDocument();

    // Inputs & Selects
    expect(screen.getByLabelText(/search channels or messages/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/narrative category/i)).toBeInTheDocument();

    // Table & EmptyState
    expect(screen.getByText('@moldova_news_pulse')).toBeInTheDocument();
    expect(screen.getByText(/no coordinated clusters in window/i)).toBeInTheDocument();

    // Tabs switching
    const tab30d = screen.getByRole('tab', { name: '30d' });
    fireEvent.click(tab30d);
    expect(tab30d).toHaveAttribute('aria-selected', 'true');

    // Modal opening and closing
    fireEvent.click(screen.getByRole('button', { name: /open evidence modal/i }));
    expect(
      screen.getByRole('dialog', { name: /cluster coordination evidence/i }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /confirm review/i }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});

