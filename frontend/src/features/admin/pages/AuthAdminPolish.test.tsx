import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppRoutes } from '../../../app/router';
import { AdminService } from '../../../services/admin.service';
import { AuthService } from '../../../services/auth.service';
import { LoginPage } from '../../auth/pages/LoginPage';
import { RegisterPage } from '../../auth/pages/RegisterPage';
import { AdminSettingsPage } from './AdminSettingsPage';

describe('Auth, Admin Settings, and Polish Views (Branch 3 of 3)', () => {
  it('enforces max 10-minute collection interval and bumps parameter version on save', async () => {
    const adminService = new AdminService();
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <AdminSettingsPage service={adminService} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Active Parameter Set: v1\.4/i)).toBeInTheDocument();
    });

    const intervalInput = screen.getByLabelText(/Collector Poll Interval/i);
    const saveButton = screen.getByRole('button', {
      name: /Save & Bump Parameter Version/i,
    });

    // Reject > 10 minutes
    fireEvent.change(intervalInput, { target: { value: '15' } });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Collection interval must be between 1 and 10 minutes/i),
      ).toBeInTheDocument();
    });

    // Accept <= 10 minutes and increment parameter version to v1.5
    fireEvent.change(intervalInput, { target: { value: '8' } });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(/Active Parameter Set: v1\.5/i)).toBeInTheDocument();
      expect(screen.getByText(/Saved new parameter version v1\.5/i)).toBeInTheDocument();
    });
  });

  it('validates login and researcher self-registration forms', async () => {
    const authService = new AuthService();
    const { unmount } = render(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage service={authService} />
      </MemoryRouter>,
    );

    const emailInput = screen.getByLabelText(/Work or Newsroom Email/i);
    fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/Enter a valid email address/i)).toBeInTheDocument();
    });
    unmount();

    render(
      <MemoryRouter initialEntries={['/register']}>
        <RegisterPage service={authService} />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole('button', { name: /register journalist account/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/Full name is required for researcher registration/i),
      ).toBeInTheDocument();
    });
  });

  it('completes registration, 6-digit email verification, and starts with clean profile', async () => {
    const authService = new AuthService();
    render(
      <MemoryRouter initialEntries={['/register']}>
        <RegisterPage service={authService} />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Full Name/i), {
      target: { value: 'Alexandru Moraru' },
    });
    fireEvent.change(screen.getByLabelText(/Username/i), {
      target: { value: 'alex_investigates' },
    });
    fireEvent.change(screen.getByLabelText(/Newsroom or Academic Email/i), {
      target: { value: 'alex@news.md' },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: 'securePassword2026' },
    });

    fireEvent.click(screen.getByRole('button', { name: /register journalist account/i }));

    await waitFor(() => {
      expect(screen.getByText(/Verify Your Email/i)).toBeInTheDocument();
      expect(screen.getByText(/Demo Verification Code/i)).toBeInTheDocument();
    });

    const codeInput = screen.getByLabelText(/6-Digit Verification Code/i);
    fireEvent.change(codeInput, { target: { value: '123456' } });
    fireEvent.click(screen.getByRole('button', { name: /verify & start investigation/i }));

    await waitFor(() => {
      expect(authService.isCleanProfile()).toBe(true);
    });
  });

  it('renders 403 UnauthorizedPage and 404 NotFoundPage for unknown routes', () => {
    const { unmount } = render(
      <MemoryRouter initialEntries={['/unauthorized']}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(
      screen.getByText('Insufficient Role Permissions (403)'),
    ).toBeInTheDocument();
    unmount();

    render(
      <MemoryRouter initialEntries={['/some-unknown-route-999']}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(screen.getByText('Page Not Found (404)')).toBeInTheDocument();
  });
});

