import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration
 * E2E and integration tests
 *
 * Project layout:
 *  - `setup` signs in a Clerk test user once and saves the session (see e2e/global.setup.ts).
 *  - The per-browser projects run the UNAUTHENTICATED specs (accessibility + example) across
 *    all 5 browsers, so a11y stays covered cross-browser and cross-viewport.
 *  - `authenticated` runs the app-functionality specs with the saved Clerk session (chromium).
 *
 * The webServer runs with NEXT_PUBLIC_API_BASE_URL unset so proxy.ts fails open (lets an
 * authenticated user reach protected pages without the billing backend, which E2E doesn't run).
 */

// Specs that must NOT be authenticated (public marketing pages + the sign-in redirect they assert).
const PUBLIC_SPECS = /(accessibility|example)\.spec\.ts/;
// Specs that require a signed-in session.
const AUTH_SPECS =
  /(notifications|templates|onboarding|billing-flow|google-docs-destination)\.spec\.ts/;

const AUTH_FILE = 'playwright/.clerk/user.json';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3001',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    { name: 'setup', testMatch: /global\.setup\.ts/ },

    // Unauthenticated public/accessibility coverage across browsers + viewports.
    { name: 'chromium', use: { ...devices['Desktop Chrome'] }, testMatch: PUBLIC_SPECS },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] }, testMatch: PUBLIC_SPECS },
    { name: 'webkit', use: { ...devices['Desktop Safari'] }, testMatch: PUBLIC_SPECS },
    { name: 'Mobile Chrome', use: { ...devices['Pixel 5'] }, testMatch: PUBLIC_SPECS },
    { name: 'Mobile Safari', use: { ...devices['iPhone 12'] }, testMatch: PUBLIC_SPECS },

    // Authenticated app-functionality specs, using the saved Clerk session.
    {
      name: 'authenticated',
      testMatch: AUTH_SPECS,
      use: { ...devices['Desktop Chrome'], storageState: AUTH_FILE },
      dependencies: ['setup'],
    },
  ],

  /* Run dev server before tests. Force fail-open billing (see proxy.ts) for authed E2E. */
  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:3001',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: { ...process.env, NEXT_PUBLIC_API_BASE_URL: '' },
  },
});
