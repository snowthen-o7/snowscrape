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
- **Framework:** Python FastAPI
- **Database:** PostgreSQL with SQLAlchemy + asyncpg
- **Migrations:** Alembic
- **Caching:** Redis
- **Task Scheduling:** APScheduler
- **Notifications:** Twilio (SMS), Web Push
- **Deployment:** Serverless (AWS Lambda)

### Infrastructure
- **Frontend Hosting:** Vercel
- **Backend Hosting:** AWS (Lambda, API Gateway)
- **Storage:** AWS S3

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
uvicorn app.main:app --reload

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

---

## Project Structure

```
SnowScrape/
├── frontend/
│   └── snowscrape/       # Next.js frontend
│       ├── app/          # App Router pages
│       ├── components/
│       │   ├── layout/   # AppLayout, AppSidebar, AppTopNav
│       │   ├── ui/       # Radix-based UI components
│       │   ├── charts/   # Recharts visualizations
│       │   └── marketing/# Landing page components
│       └── lib/          # Utilities
├── backend/
│   ├── app/              # FastAPI application
│   ├── alembic/          # Database migrations
│   └── tests/            # Python tests
└── infrastructure/       # AWS/deployment configs
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
