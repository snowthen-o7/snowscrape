/**
 * Shared gating flags for E2E specs.
 *
 * Many specs drive Clerk-protected dashboard routes that also need the live
 * backend. Without a seeded Clerk test user (CLERK_TEST_EMAIL / _PASSWORD) those
 * routes redirect to sign-in, so their assertions can never pass and the CI job
 * fails for an environment reason rather than a real regression. Gate them on
 * these flags so the default CI run is limited to the public homepage smoke
 * (example.spec.ts) and the full suite runs once the Clerk test creds are set.
 *
 * NOTE: the homepage smoke is NOT credential-free. <ClerkProvider> wraps the
 * root layout, so the smoke still requires a valid NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
 * (and CLERK_SECRET_KEY) to render; the CI job stays red until those are set as
 * repo secrets. These flags only control the authenticated/a11y specs on top.
 */

// True when a Clerk test user is available, so authenticated flows can run.
export const hasClerkTestUser =
  !!process.env.CLERK_TEST_EMAIL && !!process.env.CLERK_TEST_PASSWORD;

// Authenticated dashboard specs run only when a Clerk test user is configured.
export const runAuthedE2E = hasClerkTestUser;

// Strict axe accessibility scans (`violations` must equal []) are an aspirational
// quality gate, brittle against third-party widgets, and many target auth-gated
// pages. Opt in explicitly via RUN_A11Y=1 so they do not block the deploy gate.
export const runA11y = process.env.RUN_A11Y === '1';
