# Technical Documentation

**Last Updated**: January 2026

This guide consolidates security, accessibility, and analytics documentation.

---

## Table of Contents

1. [Security](#security)
2. [Accessibility](#accessibility)
3. [Analytics & Monitoring](#analytics--monitoring)
4. [Performance](#performance)

---

# Security

## Security Headers

All headers configured in `next.config.mjs`:

| Header | Value | Purpose |
|--------|-------|---------|
| Strict-Transport-Security | max-age=63072000; includeSubDomains; preload | Enforce HTTPS |
| X-Frame-Options | SAMEORIGIN | Prevent clickjacking |
| X-Content-Type-Options | nosniff | Prevent MIME sniffing |
| X-XSS-Protection | 1; mode=block | Browser XSS filter |
| Referrer-Policy | strict-origin-when-cross-origin | Control referrer |
| Permissions-Policy | camera=(), microphone=(), geolocation=() | Disable features |
| X-DNS-Prefetch-Control | on | DNS prefetching |
| Content-Security-Policy | [comprehensive] | XSS prevention |

## Content Security Policy

```javascript
{
  "default-src": "'self'",
  "script-src": "'self' 'unsafe-inline' 'unsafe-eval' https://clerk.accounts.dev https://challenges.cloudflare.com https://browser.sentry-cdn.com",
  "style-src": "'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src": "'self' https://fonts.gstatic.com data:",
  "img-src": "'self' data: https: blob:",
  "connect-src": "'self' https://clerk.accounts.dev https://api.snowscrape.com https://*.ingest.sentry.io",
  "frame-src": "'self' https://challenges.cloudflare.com https://clerk.accounts.dev"
}
```

## Authentication

**Provider**: Clerk

**Features:**
- Email/Password authentication
- Social OAuth (Google, GitHub)
- Multi-factor authentication (MFA)
- JWT token-based sessions
- Automatic token refresh
- CSRF protection

## Security Checklist

- [x] Environment variables for all secrets
- [x] .env.local in .gitignore
- [x] HTTPS enforced
- [x] Security headers implemented
- [x] Input validation (Zod)
- [x] XSS prevention (CSP)
- [x] Sentry error monitoring

---

# Accessibility

## WCAG 2.1 AA Compliance

SnowScrape follows WCAG 2.1 Level AA standards.

### Key Requirements

- [x] Keyboard navigation support
- [x] Screen reader compatibility
- [x] Color contrast ≥ 4.5:1 (normal text)
- [x] Color contrast ≥ 3:1 (large text)
- [x] Focus indicators visible
- [x] Alternative text for images
- [x] Semantic HTML structure
- [x] ARIA labels where appropriate

### Implementation

**Buttons and Links:**
- Descriptive text (no "click here")
- Keyboard accessible (Enter/Space)
- Disabled states announced

**Forms:**
- All inputs have labels
- Error messages associated
- Required fields indicated
- Validation announced

**Modals:**
- Focus trapped within
- ESC key closes
- Focus returns on close
- ARIA roles applied

**Tables:**
- Headers (th) used
- Caption or aria-label
- Scope attributes

### Testing

```bash
# Run accessibility tests
pnpm run test:e2e:a11y
```

**Tools Used:**
- @axe-core/playwright
- Manual keyboard testing
- Screen reader testing (NVDA/VoiceOver)

### Color Contrast

| Element | Ratio | Status |
|---------|-------|--------|
| Body text | 7.5:1 | Pass |
| Links | 4.8:1 | Pass |
| Headings | 8.2:1 | Pass |
| Buttons | 5.1:1 | Pass |

---

# Analytics & Monitoring

## Platforms

### Google Analytics 4

**Setup:**
1. Create property at analytics.google.com
2. Add Measurement ID to environment
3. Install GoogleAnalytics component
4. Update CSP

```typescript
// .env.local
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX
```

### Sentry Error Monitoring

**Configuration Files:**
- `sentry.client.config.ts`
- `sentry.server.config.ts`
- `sentry.edge.config.ts`

**Features:**
- Error tracking (client + server)
- Session replay on errors
- Performance tracing
- Release tracking

```typescript
// .env.local
NEXT_PUBLIC_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ORG=your-org
SENTRY_PROJECT=snowscrape
```

### Vercel Analytics

```bash
pnpm add @vercel/analytics
```

```typescript
// app/layout.tsx
import { Analytics } from '@vercel/analytics/react';

<Analytics />
```

## Event Tracking

```typescript
// lib/analytics.ts
export const trackEvent = (
  eventName: string,
  properties?: Record<string, any>
) => {
  // Google Analytics
  if (window.gtag) {
    window.gtag('event', eventName, properties);
  }

  // Sentry breadcrumb
  if (window.Sentry) {
    window.Sentry.addBreadcrumb({
      category: 'user-action',
      message: eventName,
      data: properties,
    });
  }
};
```

### Key Events to Track

| Event | When | Properties |
|-------|------|------------|
| sign_up | User registers | method |
| job_created | Job created | source, type |
| template_used | Template applied | template_id |
| onboarding_completed | Tour finished | steps |
| error | Error occurs | message, stack |

---

# Performance

## Build Optimizations

Configured in `next.config.mjs`:

- Source maps disabled in production
- Console.log removal
- Image optimization (AVIF, WebP)
- Package import optimizations
- Compression enabled

## Lighthouse Targets

| Metric | Target | Current |
|--------|--------|---------|
| Performance | ≥85 | - |
| Accessibility | ≥90 | - |
| Best Practices | ≥90 | - |
| SEO | ≥90 | - |

## Core Web Vitals

| Metric | Target |
|--------|--------|
| LCP | <2.5s |
| FID | <100ms |
| CLS | <0.1 |

## Running Audits

```bash
# Build production
pnpm build
pnpm start

# Run Lighthouse
pnpm lighthouse:report
```

## Bundle Analysis

```bash
# Analyze bundle size
ANALYZE=true pnpm build
```

---

## Tech Stack

| Category | Technology |
|----------|------------|
| Framework | Next.js 16.1.1 |
| React | 19.2 |
| TypeScript | 5.9 (strict) |
| Styling | Tailwind CSS 3.4 |
| UI | Radix UI + shadcn/ui |
| Auth | Clerk |
| Data | React Query 5.x |
| Validation | Zod 4.x |
| Testing | Vitest + Playwright |
| Monitoring | Sentry |
| Hosting | Vercel |
