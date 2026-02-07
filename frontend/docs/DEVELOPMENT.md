# Development Guide

**Last Updated**: January 2026

This guide consolidates all development-related documentation including local setup, testing, and workflows.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Local Development Setup](#local-development-setup)
4. [Project Structure](#project-structure)
5. [Running Tests](#running-tests)
6. [Building for Production](#building-for-production)
7. [Development Workflow](#development-workflow)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# 1. Navigate to project
cd frontend/snowscrape

# 2. Install dependencies
pnpm install

# 3. Copy environment variables
cp .env.example .env.local

# 4. Start development server
pnpm dev

# 5. Open browser
# http://localhost:3000
```

---

## Prerequisites

### Required Software

- **Node.js** v18+ ([nodejs.org](https://nodejs.org/))
- **pnpm** (Package manager): `npm install -g pnpm`
- **Git** ([git-scm.com](https://git-scm.com/))

### Optional

- **Playwright Browsers** (for E2E tests): `npx playwright install`

---

## Local Development Setup

### Environment Variables

Copy `.env.example` to `.env.local` and configure:

```bash
# Required for authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_key
CLERK_SECRET_KEY=sk_test_your_key

# API Backend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Optional - Sentry (production only)
NEXT_PUBLIC_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

### Start Development Server

```bash
pnpm dev
```

Expected output:
```
Next.js 16.1.1 (Turbopack)
- Local: http://localhost:3000
Ready in 2.1s
```

### Available Routes

**Public Pages (no auth):**
- `/` - Landing page
- `/pricing` - Pricing tiers
- `/features` - Feature showcase
- `/contact` - Contact form
- `/blog` - Blog listing

**Dashboard (requires auth):**
- `/dashboard` - Main dashboard
- `/dashboard/templates` - Template marketplace
- `/dashboard/jobs/new/visual` - Visual builder
- `/dashboard/notifications` - Notifications
- `/dashboard/analytics` - Analytics
- `/dashboard/settings` - Settings

---

## Project Structure

```
frontend/snowscrape/
├── app/                          # Next.js App Router
│   ├── (marketing)/             # Public pages
│   ├── (application)/           # Dashboard (auth required)
│   ├── layout.tsx               # Root layout
│   └── globals.css              # Global styles
├── components/                   # React components
│   ├── ui/                      # shadcn/ui components (20+)
│   ├── layout/                  # Layout components
│   └── __tests__/               # Component tests
├── lib/                         # Utilities
│   ├── api/                     # API client
│   ├── hooks/                   # React Query hooks
│   └── __tests__/               # Utility tests
├── e2e/                         # E2E tests
├── docs/                        # Documentation
└── public/                      # Static assets
```

### Key Files

- `next.config.mjs` - Next.js + Sentry config
- `tailwind.config.ts` - Tailwind theme
- `middleware.ts` - Auth middleware
- `vitest.config.ts` - Unit test config
- `playwright.config.ts` - E2E test config

---

## Running Tests

### Unit Tests (Vitest)

```bash
# Run all tests
pnpm test

# Watch mode
pnpm test -- --watch

# With UI
pnpm run test:ui

# With coverage
pnpm run test:coverage

# Specific file
pnpm test -- StatusBadge.test.tsx
```

**Current Coverage**: 42 tests passing

### E2E Tests (Playwright)

```bash
# Install browsers (first time)
npx playwright install

# Run all E2E tests
pnpm test:e2e

# With UI
pnpm run test:e2e:ui

# Headed mode
pnpm test:e2e -- --headed

# Specific browser
pnpm test:e2e -- --project=chromium
```

**Current Coverage**: 50+ scenarios

### Accessibility Tests

```bash
pnpm run test:e2e:a11y
```

**Current Coverage**: 30+ scenarios

---

## Building for Production

```bash
# Build
pnpm build

# Start production server
pnpm start

# Run Lighthouse audit
pnpm lighthouse:report
```

**Target Lighthouse Scores:**
- Performance: ≥85
- Accessibility: ≥90
- Best Practices: ≥90
- SEO: ≥90

---

## Development Workflow

### Making Changes

1. Create branch: `git checkout -b feature/your-feature`
2. Make changes (hot reload active)
3. Run tests: `pnpm test -- --run && pnpm test:e2e`
4. Commit: `git commit -m "Description"`
5. Push and create PR

### Code Quality

```bash
# Linting
pnpm lint
pnpm lint --fix

# Type checking
pnpm build
```

---

## Troubleshooting

### Port 3000 in use

```bash
# Use different port
pnpm dev -- -p 3001
```

### Dependencies issues

```bash
rm -rf node_modules
pnpm install
```

### Build errors

```bash
rm -rf .next
pnpm build
```

### Tests failing

```bash
pnpm test -- --clearCache
```

---

## Command Reference

| Command | Description |
|---------|-------------|
| `pnpm dev` | Start dev server |
| `pnpm build` | Production build |
| `pnpm start` | Start production server |
| `pnpm test` | Run unit tests |
| `pnpm test:e2e` | Run E2E tests |
| `pnpm test:e2e:a11y` | Accessibility tests |
| `pnpm lint` | Check linting |
| `pnpm lighthouse:report` | Performance audit |

---

## Additional Resources

- [Next.js Docs](https://nextjs.org/docs)
- [Tailwind Docs](https://tailwindcss.com/docs)
- [Clerk Docs](https://clerk.com/docs)
- [Playwright Docs](https://playwright.dev/)
- [Vitest Docs](https://vitest.dev/)
