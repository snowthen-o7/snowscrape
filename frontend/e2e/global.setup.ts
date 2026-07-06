import { clerk, clerkSetup } from '@clerk/testing/playwright';
import { test as setup } from '@playwright/test';

// Setup must run serially (Playwright is otherwise fully parallel).
setup.describe.configure({ mode: 'serial' });

// Fetch a Clerk Testing Token (uses CLERK_SECRET_KEY) so tests bypass bot detection.
setup('global setup', async () => {
  await clerkSetup();
});

// Relative to the Playwright cwd (frontend/), matching `storageState` in playwright.config.ts.
const authFile = 'playwright/.clerk/user.json';

setup('authenticate and save Clerk session', async ({ page }) => {
  const emailAddress = process.env.E2E_CLERK_USER_EMAIL;
  if (!emailAddress) {
    throw new Error(
      'E2E_CLERK_USER_EMAIL is not set (expected from Doppler sf-snowscrape/dev). ' +
        'It must be a Clerk test user in the instance the E2E env points at.',
    );
  }

  // Load the app so Clerk JS is present, then sign in via a server-side token (no password).
  await page.goto('/');
  await clerk.signIn({ page, emailAddress });

  // Bypass the subscription gate in proxy.ts so authenticated UI tests don't need the billing
  // backend to grant this test user a subscription. The middleware trusts a fresh "active"
  // status cookie; fetched_at is set far in the future so it is never treated as stale.
  await page.context().addCookies([
    {
      name: 'sf_sub_status',
      value: JSON.stringify({ status: 'active', fetched_at: 9_999_999_999 }),
      domain: 'localhost',
      path: '/',
      httpOnly: true,
      sameSite: 'Lax',
      expires: 9_999_999_999,
    },
  ]);

  // Confirm the session works: an authenticated, subscribed user reaches /dashboard rather than
  // being bounced to /sign-in or /onboarding/checkout.
  await page.goto('/dashboard');
  await page.waitForURL(/\/dashboard/, { timeout: 15_000 });

  await page.context().storageState({ path: authFile });
});
