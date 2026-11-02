import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

const defaultQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export interface AppProvidersProps {
  children: React.ReactNode;
}

export function AppProviders({ children }: AppProvidersProps) {
  return <QueryClientProvider client={defaultQueryClient}>{children}</QueryClientProvider>;
}

