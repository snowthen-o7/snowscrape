# SnowScrape - AI Development Context

## Project Identity

**SnowScrape** is a modern web scraping platform with no-code job creation, scheduled scraping, JavaScript rendering, and proxy rotation.

**This is the REFERENCE IMPLEMENTATION for the unified SnowForge LLC UI design system.**

**Package Manager:** pnpm (ALWAYS use pnpm, never npm or yarn)

---

## Tech Stack

### Frontend (frontend/snowscrape)
- **Framework:** Next.js (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS 3.x
- **UI Components:** Radix UI (accordion, checkbox, dialog, dropdown-menu, icons, label, popover, progress, select, separator, slot, switch, tabs, toast, tooltip)
- **State:** TanStack React Query
- **Forms:** React Hook Form + Zod
- **Charts:** Recharts
- **Auth:** Clerk
- **Monitoring:** Sentry
- **Testing:** Vitest, Playwright, Lighthouse

### Backend (backend)
- **Framework:** Python (AWS Lambda handlers, not FastAPI)
- **Database:** DynamoDB (7 tables, PAY_PER_REQUEST billing)
- **Caching:** In-memory per Lambda container (Redis planned, not yet implemented)
- **Task Scheduling:** CloudWatch Events (5-min interval) + SQS job queue
- **Notifications:** Webhooks (SQS-based delivery with DLQ)
- **Deployment:** Serverless Framework (AWS Lambda + API Gateway)
- **Monitoring:** CloudWatch, X-Ray tracing, SnowGlobe Observatory

### Infrastructure
- **Frontend Hosting:** Vercel (region: iad1)
- **Backend Hosting:** AWS Lambda (29 functions) + API Gateway (us-east-2)
- **Storage:** AWS S3 (results bucket with Glacier lifecycle)
- **Queues:** SQS (job queue + webhook queue, each with DLQ)
- **Secrets:** AWS SSM Parameter Store (Clerk keys, proxy credentials)

---

## Commands

### Frontend (from frontend/snowscrape)
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

### Backend (from backend)
```bash
# Python environment
pip install -r requirements.txt

# Local development (requires AWS credentials)
sls invoke local -f healthCheck

# Deploy
sls deploy --stage dev

# Deploy single function
sls deploy function -f createJob --stage dev

# View logs
sls logs -f createJob --stage dev --tail
```

---

## Project Structure

```
SnowScrape/
├── frontend/
│   └── snowscrape/       # Next.js frontend
│       ├── app/          # App Router pages
│       │   ├── (application)/  # Protected dashboard routes
│       │   └── (marketing)/    # Public marketing pages
│       ├── components/
│       │   ├── layout/   # SnowScrapeLayout, AppSidebar, AppTopNav
│       │   ├── ui/       # Radix-based UI components
│       │   ├── charts/   # Recharts visualizations
│       │   └── marketing/# Landing page components
│       └── lib/          # Utilities, hooks, API client
├── backend/
│   ├── handler.py        # Lambda function handlers (~2800 lines)
│   ├── serverless.yml    # Serverless Framework config (AWS resources)
│   ├── job_manager.py    # Job CRUD operations
│   ├── crawl_manager.py  # URL crawling and query execution
│   ├── tiered_scraper.py # 4-tier scraping system
│   ├── validators.py     # Input validation (XPath, regex, URLs)
│   ├── proxy_manager.py  # Proxy rotation logic
│   ├── webhook_dispatcher.py     # Webhook event dispatching
│   ├── webhook_delivery_handler.py # SQS-triggered webhook delivery
│   ├── connection_pool.py # DynamoDB/S3/SQS connection reuse
│   ├── logger.py         # Structured JSON logging
│   └── tests/            # pytest + moto tests
└── docs/                 # Architecture and deployment docs
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

- ALWAYS use pnpm for frontend, pip for backend
- Clerk for authentication
- TanStack Query for API state management
- React Hook Form + Zod for form validation
- Radix UI for accessible components
- Recharts for data visualization
- Maintain backward compatibility with AWS Lambda backend

## Styling Guidelines

**CRITICAL: Always use semantic CSS variable-based classes for proper dark mode support**

### ❌ NEVER use hardcoded Tailwind colors:
```tsx
// WRONG - These won't adapt to dark mode
<div className="bg-white text-gray-900 border-gray-200">
<p className="text-gray-500">Description</p>
<button className="bg-blue-600 text-white">Click</button>
```

### ✅ ALWAYS use semantic color classes:
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
- ✅ New AWS resources
- ✅ Changes to existing resources
- ✅ New third-party services or API integrations
- ✅ Environment variable additions/changes
- ✅ Deployment architecture changes
- ✅ Security policy updates
- ✅ Cost optimization strategies
- ✅ Backup and disaster recovery procedures

This ensures the entire team has accurate, up-to-date information about the infrastructure.

