/**
 * Example E2E Test
 * Playwright end-to-end test example
 */

import { test, expect } from '@playwright/test';

test.describe('Homepage', () => {
  test('should load the homepage', async ({ page }) => {
    await page.goto('/');

    // Check that the page loaded
    await expect(page).toHaveTitle(/SnowScrape|Create Next App/);
  });

  test('should have navigation links', async ({ page }) => {
    await page.goto('/');

    // Check for common navigation elements
    // Note: Update these selectors based on your actual homepage
    const links = page.locator('a');
    await expect(links).not.toHaveCount(0);
  });
});

test.describe('Dashboard (authenticated)', () => {
  test.skip('should require authentication', async ({ page }) => {
    // Skip this test if authentication is not set up in test environment
    await page.goto('/dashboard');

    // Should redirect to sign-in page
    await expect(page).toHaveURL(/sign-in/);
  });
});

test.describe('Accessibility', () => {
  test('should not have automatically detectable accessibility issues', async ({
    page,
  }) => {
    await page.goto('/');

    // Basic accessibility checks
    // For more comprehensive checks, use @axe-core/playwright
    const html = await page.locator('html');
    await expect(html).toHaveAttribute('lang');
  });
});
