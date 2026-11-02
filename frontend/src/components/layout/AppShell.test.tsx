import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppRoutes } from '../../app/router';

describe('AppShell Layout (Sidebar, Topbar, RightPanel)', () => {
  it('renders 3-column shell with brand logo, nav items, Statics widget, Topbar, and RightPanel', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <AppRoutes />
      </MemoryRouter>,
    );

    // Brand & Main Hero
    expect(screen.getByText('Scamguard')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /hello analyst/i })).toBeInTheDocument();

    // Sidebar Statics mini widget
    expect(screen.getByText('Statics')).toBeInTheDocument();
    expect(screen.getByText('Max')).toBeInTheDocument();
    expect(screen.getByText('Min')).toBeInTheDocument();

    // RightPanel analyst profile, quick cards, and Audit radial gauge
    expect(screen.getByText('Elena Botnari')).toBeInTheDocument();
    expect(screen.getByText('Lead Researcher')).toBeInTheDocument();
    expect(screen.getByText('3502')).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('38%')).toBeInTheDocument();
  });

  it('supports sidebar collapse, locale cycling, range selection, and mobile drawer toggle', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <AppRoutes />
      </MemoryRouter>,
    );

    // Collapse desktop sidebar
    const collapseBtn = screen.getByRole('button', { name: /collapse sidebar/i });
    fireEvent.click(collapseBtn);
    expect(screen.getByRole('button', { name: /expand sidebar/i })).toBeInTheDocument();

    // Cycle language EN -> RO -> RU
    const localeBtn = screen.getByRole('button', { name: /switch language/i });
    expect(localeBtn).toHaveTextContent('EN');
    fireEvent.click(localeBtn);
    expect(localeBtn).toHaveTextContent('RO');

    // Change time range
    const rangeSelect = screen.getByLabelText(/analysis time range/i);
    fireEvent.change(rangeSelect, { target: { value: '30d' } });
    expect(rangeSelect).toHaveValue('30d');

    // Open and close mobile drawer
    const openMenuBtn = screen.getByRole('button', { name: /open navigation menu/i });
    fireEvent.click(openMenuBtn);
    expect(screen.getByRole('dialog', { name: /mobile navigation menu/i })).toBeInTheDocument();

    const closeMenuBtn = screen.getByRole('button', { name: /close navigation drawer/i });
    fireEvent.click(closeMenuBtn);
    expect(
      screen.queryByRole('dialog', { name: /mobile navigation menu/i }),
    ).not.toBeInTheDocument();
  });

  it('navigates across routes from sidebar links and search bar submission', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <AppRoutes />
      </MemoryRouter>,
    );

    // Click Clusters link in sidebar
    const clustersLink = screen.getByRole('link', { name: /clusters/i });
    fireEvent.click(clustersLink);
    expect(
      screen.getByRole('heading', { name: /coordinated clusters/i }),
    ).toBeInTheDocument();

    // Submit search query in Topbar
    const searchInput = screen.getByLabelText(/search channels, messages, or clusters/i);
    fireEvent.change(searchInput, { target: { value: 'chisinau' } });
    fireEvent.submit(screen.getByRole('search'));
    expect(
      screen.getByRole('heading', { name: /messages & narrative search/i }),
    ).toBeInTheDocument();
  });
});

