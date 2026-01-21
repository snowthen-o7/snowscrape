/**
 * React Query Configuration
 * Central configuration for data fetching and caching
 */

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Stale time: Data is considered fresh for 30 seconds
      staleTime: 30000,

      // Cache time: Unused data stays in cache for 5 minutes
      gcTime: 300000,

      // Retry failed requests twice
      retry: 2,

      // Don't refetch on window focus (can be overwhelming during development)
      refetchOnWindowFocus: false,

      // Refetch on reconnect
      refetchOnReconnect: true,
    },
    mutations: {
      // Retry failed mutations once
      retry: 1,
    },
  },
});
