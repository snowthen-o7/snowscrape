import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useSubscription } from '@/lib/hooks/useSubscription';

vi.mock('@clerk/nextjs', () => ({
  useSession: () => ({
    session: { getToken: async () => 'test-token' },
  }),
}));

vi.mock('@/lib/api', () => ({
  billingAPI: {
    getSubscription: vi.fn(),
  },
}));

import { billingAPI } from '@/lib/api';

beforeEach(() => {
  vi.clearAllMocks();
  process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.test';
});

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('useSubscription', () => {
  it('returns subscription data on success', async () => {
    (billingAPI.getSubscription as any).mockResolvedValue({
      plan: 'pro',
      status: 'trialing',
      monthly_page_limit: 25000,
      monthly_pages_used: 0,
    });
    const { result } = renderHook(() => useSubscription(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data?.plan).toBe('pro');
    expect(result.current.data?.status).toBe('trialing');
  });
});
