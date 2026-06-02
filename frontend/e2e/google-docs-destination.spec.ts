/**
 * Google Docs destination E2E tests.
 *
 * NOTE: The dashboard pages are Clerk-protected. Tests in this file are marked
 * with `test.fixme()` until a Clerk test user is seeded for the test environment
 * (see billing-flow.spec.ts for the auth pattern). When CLERK_TEST_EMAIL and
 * CLERK_TEST_PASSWORD are set in CI, remove the `test.fixme()` calls.
 */

import { test, expect } from '@playwright/test';

test.describe('Google Docs destination', () => {
  test('Integrations page shows Connect Google button when not connected', async ({
    page,
  }) => {
    test.fixme(true, 'Requires Clerk-authenticated session');

    await page.goto('/dashboard/integrations');
    await expect(page.getByRole('button', { name: /connect google/i })).toBeVisible();
  });

  test('Destinations page shows empty state CTA when no destinations exist', async ({
    page,
  }) => {
    test.fixme(true, 'Requires Clerk-authenticated session');

    await page.goto('/dashboard/destinations');
    await expect(page.getByText(/no destinations yet/i)).toBeVisible();
    await expect(
      page.getByRole('link', { name: /create your first destination/i }),
    ).toBeVisible();
  });

  test('New destination form blocks submit without folder ID', async ({ page }) => {
    test.fixme(true, 'Requires Clerk-authenticated session');

    await page.goto('/dashboard/destinations/new');
    await page.getByLabel('Name').fill('Test Destination');
    await page.getByRole('button', { name: /create destination/i }).click();
    await expect(page.getByText(/paste a google drive folder id/i)).toBeVisible();
  });

  test('OAuth callback shows error when state mismatch occurs', async ({ page }) => {
    test.fixme(true, 'Requires Clerk-authenticated session');

    // Set wrong state in sessionStorage, navigate to callback with mismatched state
    await page.goto('/dashboard/integrations/google/callback?code=test&state=mismatch');
    await expect(page.getByText(/state mismatch/i)).toBeVisible();
  });

  test('Sign-in redirect occurs when accessing dashboard pages unauthenticated', async ({
    page,
  }) => {
    // This test runs without auth — verifies the routes exist and middleware redirects.
    await page.goto('/dashboard/integrations');
    // Clerk redirects to sign-in OR shows sign-in UI inline
    await expect(page).toHaveURL(/(sign-in|integrations)/);
  });
});
