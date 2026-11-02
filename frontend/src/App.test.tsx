import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { App } from './App';

describe('App', () => {
  it('renders Scamguard shell and navigation', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText('Scamguard')).toBeInTheDocument();
    });
    expect(screen.getByRole('navigation', { name: /main navigation/i })).toBeInTheDocument();
  });
});
