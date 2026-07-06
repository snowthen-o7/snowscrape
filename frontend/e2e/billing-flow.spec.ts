import { test, expect } from '@playwright/test';

/**
 * NOTE: Requires a Clerk test user pre-seeded for the test environment.
 * Set CLERK_TEST_EMAIL and CLERK_TEST_PASSWORD in .env.test, and ensure
 * the Clerk dashboard has the test user without a SnowScrape subscription.
 */

test.describe('Billing flow E2E', () => {
  // The subscription-gated redirect can only be asserted with the billing backend running
  // (proxy.ts reads status from ${NEXT_PUBLIC_API_BASE_URL}/billing/subscription). The E2E env
  // runs the frontend with billing failing open, so this needs the backend + a seeded
  // no-subscription state before it can be enabled. The auth fixture covers signed-in UI only.
  test.fixme('signed-in user with no subscription is redirected to /onboarding/checkout', async ({
    page,
  }) => {
    await page.goto('/sign-in');
    await page.fill('input[name="identifier"]', process.env.CLERK_TEST_EMAIL!);
    await page.click('button[type="submit"]');
    await page.fill('input[name="password"]', process.env.CLERK_TEST_PASSWORD!);
    await page.click('button[type="submit"]');

    // Land somewhere; middleware should redirect to /onboarding/checkout.
    await page.waitForURL(/\/onboarding\/checkout/, { timeout: 15_000 });
    await expect(page.getByRole('heading', { name: /14-day Pro trial/i })).toBeVisible();
  });

  test('create-API-key modal shows raw key once and gates close', async ({ page }) => {
    test.fixme(true, 'Requires authenticated session with active subscription — set up in CI before enabling');
  });
});
