import { describe, it, expect, vi, beforeEach } from 'vitest';

// Hoist env setup so it runs before module graph is evaluated.
const { setEnv } = vi.hoisted(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.test';
  return {
    setEnv: () => {
      process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.test';
    },
  };
});

import { billingAPI } from '@/lib/api/billing';

beforeEach(() => {
  setEnv();
  vi.restoreAllMocks();
});

describe('billingAPI.getSubscription', () => {
  it('returns parsed subscription dto', async () => {
    const mockJson = {
      plan: 'pro',
      status: 'trialing',
      current_period_end: '2026-06-01',
      trial_end: '2026-05-20',
      cancel_at_period_end: false,
      monthly_page_limit: 25000,
      monthly_pages_used: 100,
      concurrent_job_limit: 5,
      features: {
        js_rendering: true,
        proxy_rotation: true,
        webhooks: true,
        anti_bot: false,
      },
      has_billing_account: true,
    };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => mockJson,
    } as any);

    const result = await billingAPI.getSubscription('test-token');
    expect(result).toEqual(mockJson);
    expect(global.fetch).toHaveBeenCalledWith(
      'https://api.test/billing/subscription',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token',
        }),
      })
    );
  });
});

describe('billingAPI.createCheckoutSession', () => {
  it('posts is_trial flag and returns checkout_url', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => ({ checkout_url: 'https://stripe.test/cs' }),
    } as any);

    const result = await billingAPI.createCheckoutSession('t', {
      plan: 'pro',
      is_trial: true,
    });
    expect(result.checkout_url).toBe('https://stripe.test/cs');
    const call = (global.fetch as any).mock.calls[0];
    const body = JSON.parse(call[1].body as string);
    expect(body).toEqual({ plan: 'pro', is_trial: true });
  });
});
