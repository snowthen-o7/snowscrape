# SnowScrape - AI Development Context

## Project Identity

**SnowScrape** is a modern web scraping platform with no-code job creation, scheduled scraping, JavaScript rendering, and proxy rotation.

**This is the REFERENCE IMPLEMENTATION for the unified SnowForge LLC UI design system.**

**Package Manager:** pnpm (ALWAYS use pnpm, never npm or yarn)

---

## Tech Stack

### Frontend (frontend/)
- **Framework:** Next.js (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS v4.x
- **UI Components:** Radix UI (accordion, checkbox, dialog, dropdown-menu, icons, label, popover, progress, select, separator, slot, switch, tabs, toast, tooltip)
- **State:** TanStack React Query
- **Forms:** React Hook Form + Zod
- **Charts:** Recharts
- **Auth:** Clerk
- **Monitoring:** Sentry
- **Testing:** Vitest, Playwright, Lighthouse

### Backend (backend/)
- **Framework:** Python (AWS Lambda handlers)
- **Database:** DynamoDB (8 tables, PAY_PER_REQUEST billing)
- **Caching:** In-memory per Lambda container (Redis planned)
- **Task Scheduling:** CloudWatch Events (5-min interval) + SQS job queue
- **Notifications:** Webhooks (SQS-based delivery with DLQ)
- **Deployment:** SST Ion (TypeScript IaC, Pulumi engine)
- **Python Deps:** uv + pyproject.toml
- **Monitoring:** CloudWatch, X-Ray tracing, SnowGlobe Observatory

### Infrastructure
- **IaC:** SST Ion v3 (`sst.config.ts`) — replaces Serverless Framework
- **Frontend Hosting:** Vercel (region: iad1)
- **Backend Hosting:** AWS Lambda + API Gateway V2 (us-east-2)
- **Storage:** AWS S3 (results bucket with Glacier lifecycle)
- **Queues:** SQS (job queue + webhook queue, each with DLQ)
- **Secrets:** SST Secrets (linked to SSM Parameter Store)

---

## Commands

### Root (monorepo)
```bash
pnpm install              # Install all workspace dependencies
pnpm dev                  # Start frontend dev server (port 3001)
pnpm build                # Build frontend
pnpm lint                 # Lint frontend
pnpm test                 # Run frontend unit tests
pnpm test:e2e             # Run frontend E2E tests

# SST Ion (Infrastructure)
pnpm sst:dev              # Live dev mode (hot reload Lambdas)
pnpm sst:deploy           # Deploy to dev stage
pnpm sst:deploy:prod      # Deploy to prod stage
pnpm sst:remove           # Tear down dev stage
```

### Frontend (from frontend/)
```bash
pnpm dev              # Start dev server (port 3001)
pnpm build            # Production build
pnpm start            # Start production server
pnpm lint             # Run ESLint
pnpm test             # Run Vitest
pnpm test:ui          # Vitest UI
pnpm test:coverage    # Coverage report
pnpm test:e2e         # Run Playwright
pnpm test:e2e:ui      # Playwright UI
pnpm lighthouse       # Run Lighthouse CI
```

### Backend (from root)
```bash
# Python environment (using uv)
uv sync                   # Install Python dependencies
uv run pytest backend/tests/ -v  # Run backend tests

# SST deployment
npx sst deploy --stage dev       # Deploy backend to dev
npx sst deploy --stage prod      # Deploy backend to prod
npx sst dev                      # Live dev mode
```

---

## Project Structure

```
snowscrape/                          # Root = SST Ion project + monorepo
├── sst.config.ts                    # Infrastructure-as-code (TypeScript)
├── package.json                     # Root: SST deps + pnpm workspace scripts
├── pnpm-workspace.yaml              # pnpm workspace config
├── pyproject.toml                   # uv workspace root (for Python Lambda)
├── tsconfig.json                    # For sst.config.ts compilation
├── .gitignore
├── frontend/                        # Next.js app
│   ├── app/                         # App Router pages
│   │   ├── (application)/           # Protected dashboard routes
│   │   └── (marketing)/             # Public marketing pages
│   ├── components/
│   │   ├── layout/                  # AppLayout, AppSidebar, AppTopNav
│   │   ├── ui/                      # Radix-based UI components
│   │   ├── charts/                  # Recharts visualizations
│   │   └── marketing/               # Landing page components
│   ├── lib/                         # Utilities, hooks, API client
│   └── package.json
├── backend/                         # Python Lambda handlers
│   ├── pyproject.toml               # uv workspace member
│   ├── handler.py                   # Main handler (~2800 lines, 26 functions)
│   ├── websocket_handler.py         # WebSocket handlers
│   ├── webhook_delivery_handler.py  # SQS webhook delivery
│   ├── job_manager.py               # Job CRUD operations
│   ├── crawl_manager.py             # URL crawling and query execution
│   ├── tiered_scraper.py            # 4-tier scraping system
│   ├── validators.py                # Input validation (XPath, regex, URLs)
│   ├── proxy_manager.py             # Proxy rotation logic
│   ├── connection_pool.py           # DynamoDB/S3/SQS connection reuse
│   ├── logger.py                    # Structured JSON logging
│   ├── openapi.yml                  # API spec
│   └── tests/                       # pytest + moto tests
├── infrastructure/                  # CloudFormation proxy stack
│   ├── proxy-stack.yml
│   └── deploy-proxies.sh
├── docs/
│   └── INFRASTRUCTURE.md
├── .github/
│   └── workflows/
│       ├── frontend.yml             # Frontend CI (lint, test, build)
│       └── backend.yml              # Backend CI + SST deploy
├── .claude/
│   └── CLAUDE.md
├── docker-compose.yml
└── README.md
```

---

## Reference UI Components

**This repo contains the reference sidebar implementation for all SnowForge LLC apps.**

### AppLayout (`components/layout/AppLayout.tsx`)
- Flex container with sidebar + main content
- Mobile-responsive with overlay sidebar
- Uses `AppSidebar` and `AppTopNav`

### AppSidebar (`components/layout/AppSidebar.tsx`)
- Collapsible: `w-16` (collapsed) / `w-64` (expanded)
- Logo section with collapse toggle button
- Quick action button (context-specific CTA)
- Icon navigation with active/hover states:
  - Active: `bg-primary text-primary-foreground`
  - Hover: `hover:bg-muted text-muted-foreground hover:text-foreground`
- Uses lucide-react icons
- Recent items footer section (when expanded)

---

## SnowForge LLC Unification Goals

This repository serves as the **reference implementation** for the unified SnowForge LLC design system.

### UI Pattern to Replicate
All sister apps (SnowPipe, SnowGen, SnowGlobe) should adopt:
1. The `AppLayout` pattern with responsive sidebar
2. The `AppSidebar` collapsible navigation pattern
3. Consistent Radix UI component usage
4. Unified color tokens and Tailwind config

### Sister Repositories
- **SnowForge** - Landing page
- **SnowGen** - AI content generation
- **SnowGlobe** - Analytics dashboard
- **SnowPipe** - Data pipeline management
- **SnowSite** - Personal/portfolio site (Astro - different stack)
- **SnowSports** - Sports analytics (Python backend)
- **TrueIce** - League of Legends analytics

---

## Critical Rules

- ALWAYS use pnpm for frontend, uv for backend Python
- Clerk for authentication
- TanStack Query for API state management
- React Hook Form + Zod for form validation
- Radix UI for accessible components
- Recharts for data visualization
- SST Ion for infrastructure-as-code (never Serverless Framework)
- Maintain backward compatibility with AWS Lambda backend

## Styling Guidelines

**CRITICAL: Always use semantic CSS variable-based classes for proper dark mode support**

### NEVER use hardcoded Tailwind colors:
```tsx
// WRONG - These won't adapt to dark mode
<div className="bg-white text-gray-900 border-gray-200">
<p className="text-gray-500">Description</p>
<button className="bg-blue-600 text-white">Click</button>
```

### ALWAYS use semantic color classes:
```tsx
// CORRECT - These automatically adapt to dark mode
<div className="bg-card text-card-foreground border-border">
<p className="text-muted-foreground">Description</p>
<button className="bg-primary text-primary-foreground">Click</button>
```

### Available Semantic Color Classes:
- **Layout**: `bg-background`, `text-foreground`
- **Cards**: `bg-card`, `text-card-foreground`, `border-border`
- **Primary Actions**: `bg-primary`, `text-primary-foreground`
- **Secondary**: `bg-secondary`, `text-secondary-foreground`
- **Muted/Subtle**: `bg-muted`, `text-muted-foreground`
- **Accents**: `bg-accent`, `text-accent-foreground`
- **Destructive**: `bg-destructive`, `text-destructive-foreground`
- **Inputs**: `border-input`, `ring-ring`

### Status Badges (need dark mode variants):
```tsx
// Use conditional dark mode classes for colored badges
className={`
  bg-green-100 text-green-800
  dark:bg-green-900/30 dark:text-green-400
`}
```

### Why This Matters:
- Hardcoded colors (like `bg-white`, `text-gray-900`) don't change with theme
- Semantic classes use CSS variables that automatically switch with dark mode
- This ensures a consistent, professional dark mode experience

## Infrastructure Documentation

**IMPORTANT: Maintain `docs/INFRASTRUCTURE.md` for all infrastructure changes**

The infrastructure documentation (`docs/INFRASTRUCTURE.md`) is the single source of truth for:
- AWS resources
- Database configuration
- Third-party services
- Environment variables
- Deployment architecture
- Cost tracking
- Security policies

**Rules for Infrastructure Changes:**
1. **Before making infrastructure changes**: Read `docs/INFRASTRUCTURE.md` to understand current setup
2. **After making infrastructure changes**: Update `docs/INFRASTRUCTURE.md` immediately
3. **Update the Change Log**: Add an entry with date, change description, and author
4. **Update "Last Updated" date**: Keep the header current
5. **Monthly Review**: Review and update the document monthly

**What requires documentation updates:**
- New AWS resources
- Changes to existing resources
- New third-party services or API integrations
- Environment variable additions/changes
- Deployment architecture changes
- Security policy updates
- Cost optimization strategies
- Backup and disaster recovery procedures

This ensures the entire team has accurate, up-to-date information about the infrastructure.
