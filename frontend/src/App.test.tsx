import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { App } from './App';
import { authService } from './services/auth.service';

describe('App', () => {
  it('renders ScamGuard shell and navigation', async () => {
    await authService.login({ email: 'elena.botnari@scamguard.md', password: 'scamguard2026' });
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText('ScamGuard')).toBeInTheDocument();
    });
    expect(screen.getByRole('navigation', { name: /main navigation/i })).toBeInTheDocument();
  });
});
