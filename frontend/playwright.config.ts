import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration
 * E2E and integration tests
 */

// The dev server binds port 3001 (see package.json `dev`: `next dev -p 3001`).
// baseURL and webServer.url MUST match it, or Playwright's webServer wait times
// out and the whole job fails before any test runs. The port is fixed to match
// the `dev` script; override the whole URL with PLAYWRIGHT_BASE_URL if needed.
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3001';

// In CI, run a single engine (chromium). The smoke suite does not need
// cross-browser coverage, and 5 engines at workers:1 with retries was slow and
// flaky. Local runs keep the full matrix.
const allProjects = [
  { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  { name: 'Mobile Chrome', use: { ...devices['Pixel 5'] } },
  { name: 'Mobile Safari', use: { ...devices['iPhone 12'] } },
];
const ciProjects = allProjects.filter((p) => p.name === 'chromium');

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: process.env.CI ? ciProjects : allProjects,

  /* Run dev server before tests */
  webServer: {
    command: 'pnpm dev',
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    // Cold Next dev start (plus building the @snowforge/ui git dependency) can
    // exceed the 60s default on CI; give it room before declaring a timeout.
    timeout: 120_000,
    // The spawned dev server inherits process.env by default, so Clerk keys
    // (NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY) set by the CI job
    // flow through to <ClerkProvider> without an explicit env allowlist here.
  },
});
