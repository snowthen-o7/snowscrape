# SnowScrape Frontend

Modern Next.js 16 web application for managing and monitoring web scraping jobs, built with React 19, TypeScript, and Tailwind CSS.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Setup](#setup)
- [Development](#development)
- [Building](#building)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Components](#components)
- [Authentication](#authentication)
- [API Integration](#api-integration)
- [Styling](#styling)
- [Troubleshooting](#troubleshooting)

---

## Overview

The frontend provides a dashboard for users to:
- Create and configure scraping jobs
- View job status and execution history
- Pause, resume, and delete jobs
- Refresh jobs to re-crawl URLs
- Monitor job progress (coming in Phase 8)

---

## Tech Stack

### Core

- **Next.js 16.1** - React framework with App Router
- **React 19.2** - UI library with Server Components
- **TypeScript 5.9** - Type-safe JavaScript
- **Tailwind CSS 3.4** - Utility-first CSS framework

### UI Components

- **Radix UI** - Headless component primitives
  - Checkbox, Icons, Label, Select, Slot, Switch
- **Lucide React** - Icon library
- **React Toastify** - Toast notifications
- **clsx** + **tailwind-merge** - Conditional class merging
- **class-variance-authority** - Component variants

### Authentication

- **Clerk** - User authentication and management

### Data Handling

- **PapaParse** - CSV parsing
- **jsonpath** - JSON path queries

### Development Tools

- **ESLint** - Code linting
- **PostCSS** - CSS processing
- **pnpm** - Fast, disk space efficient package manager

---

## Setup

### Prerequisites

- Node.js 20+
- pnpm 10+ (install with `npm install -g pnpm`)
- Clerk account (for authentication)
- SnowScrape backend deployed and accessible

### 1. Install Dependencies

```bash
cd frontend/snowscrape

# Install all dependencies
pnpm install
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env.local

# Edit .env.local and add your configuration
```

**Required environment variables:**

```bash
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx

# Clerk Redirect URLs (optional, defaults shown)
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard

# Backend API URL
NEXT_PUBLIC_API_URL=https://your-api-gateway-url.amazonaws.com/dev
```

### 3. Run Development Server

```bash
pnpm dev
```

Visit [http://localhost:3000](http://localhost:3000)

---

## Development

### Development Server

```bash
# Start dev server (default port 3000)
pnpm dev

# Start on different port
pnpm dev -p 3001

# Start with turbo mode (faster)
pnpm dev --turbo
```

### Linting

```bash
# Run ESLint
pnpm lint

# Fix auto-fixable issues
pnpm lint --fix
```

### Type Checking

```bash
# TypeScript type checking
npx tsc --noEmit
```

---

## Building

### Production Build

```bash
# Build for production
pnpm build

# Build output will be in .next/ directory
```

### Preview Production Build

```bash
# Build and start production server
pnpm build && pnpm start
```

### Build Issues

If you encounter build errors:

1. **Missing environment variables**
   - Ensure `.env.local` has all required variables
   - Clerk keys are mandatory for build

2. **TypeScript errors**
   - Fix type errors before building
   - Use `npx tsc --noEmit` to check

3. **Dependency conflicts**
   - Clear node_modules and reinstall:
     ```bash
     rm -rf node_modules .next
     pnpm install
     ```

---

## Deployment

### Vercel (Recommended)

The project is optimized for Vercel deployment:

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy to production
vercel --prod

# Deploy to preview
vercel
```

**Vercel Configuration:**

1. Connect your GitHub repository to Vercel
2. Set environment variables in Vercel dashboard:
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
   - `CLERK_SECRET_KEY`
   - `NEXT_PUBLIC_API_URL`
3. Deploy automatically on push to main branch

### Other Platforms

The app can be deployed to any platform supporting Next.js:

- **Netlify**: Use the Next.js plugin
- **AWS Amplify**: Configure with Next.js SSR
- **Docker**: Create Dockerfile with Node.js base image
- **Self-hosted**: Use `pnpm build && pnpm start`

---

## Project Structure

```
frontend/snowscrape/
├── app/                      # Next.js App Router
│   ├── (application)/       # Authenticated routes
│   │   └── dashboard/       # Dashboard page
│   ├── (auth)/              # Auth routes
│   │   ├── sign-in/         # Sign in page
│   │   └── sign-up/         # Sign up page
│   ├── api/                 # API routes (if any)
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Home/landing page
│   └── globals.css          # Global styles
│
├── components/               # React components
│   ├── ui/                  # Reusable UI components
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── select.tsx
│   │   └── ...
│   ├── JobModal.tsx         # Job creation/edit modal
│   └── ...
│
├── lib/                     # Utilities and helpers
│   └── utils.ts            # Utility functions
│
├── public/                  # Static assets
│   └── ...
│
├── middleware.ts            # Next.js middleware (auth)
├── next.config.js          # Next.js configuration
├── tailwind.config.ts      # Tailwind CSS config
├── tsconfig.json           # TypeScript config
├── postcss.config.mjs      # PostCSS config
├── .env.example            # Environment variables template
└── package.json            # Dependencies and scripts
```

---

## Components

### Key Components

#### JobModal
**Location:** `components/JobModal.tsx`
**Purpose:** Create and edit scraping jobs
**Features:**
- Form validation
- CSV file source configuration
- Query builder (XPath, Regex, JSONPath)
- Schedule configuration
- Concurrency settings

#### Dashboard Page
**Location:** `app/(application)/dashboard/page.tsx`
**Purpose:** Main dashboard for job management
**Features:**
- List all user jobs
- Job status indicators
- Action buttons (pause, refresh, delete)
- Create new job button

### UI Components (Radix UI)

All UI components are in `components/ui/`:

- **Button** - Customizable button with variants
- **Input** - Form input fields
- **Select** - Dropdown select component
- **Label** - Form labels
- **Checkbox** - Toggle checkboxes
- **Switch** - Toggle switches

**Usage Example:**

```tsx
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function MyComponent() {
  return (
    <div>
      <Input placeholder="Enter job name" />
      <Button variant="default">Submit</Button>
    </div>
  );
}
```

---

## Authentication

### Clerk Integration

Authentication is handled by Clerk with middleware protection.

#### Middleware (`middleware.ts`)

```typescript
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

const isPublicRoute = createRouteMatcher(['/', '/sign-in(.*)', '/sign-up(.*)']);

export default clerkMiddleware(async (auth, request) => {
  const authObject = await auth();

  if (!isPublicRoute(request) && !authObject.userId) {
    return Response.redirect(new URL('/sign-in', request.url));
  }
});
```

#### Protected Routes

- `/dashboard` - Requires authentication
- All routes under `(application)` - Requires authentication

#### Public Routes

- `/` - Landing page
- `/sign-in` - Sign in page
- `/sign-up` - Sign up page
- `/api/health` - Health check

#### Getting User Info

```tsx
import { useUser } from '@clerk/nextjs';

export default function MyComponent() {
  const { user, isLoaded, isSignedIn } = useUser();

  if (!isLoaded) return <div>Loading...</div>;
  if (!isSignedIn) return <div>Not signed in</div>;

  return <div>Hello {user.firstName}!</div>;
}
```

#### Getting Auth Token

```tsx
import { useAuth } from '@clerk/nextjs';

export default function MyComponent() {
  const { getToken } = useAuth();

  const fetchData = async () => {
    const token = await getToken();
    const response = await fetch(`${API_URL}/jobs`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    // ...
  };
}
```

---

## API Integration

### API Client

API calls are made directly in components using fetch:

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL;

// Get auth token
const { getToken } = useAuth();
const token = await getToken();

// Make API request
const response = await fetch(`${API_URL}/jobs`, {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
});

const data = await response.json();
```

### API Endpoints

See [backend/README.md](../../backend/README.md) for full API documentation.

**Common endpoints:**

- `GET /jobs` - List all jobs
- `POST /jobs` - Create job
- `GET /jobs/{id}` - Get job details
- `PUT /jobs/{id}` - Update job
- `DELETE /jobs/{id}` - Delete job
- `POST /jobs/{id}/pause` - Pause/resume job
- `POST /jobs/{id}/refresh` - Refresh job

---

## Styling

### Tailwind CSS

The project uses Tailwind CSS 3 with custom configuration.

#### Tailwind Config (`tailwind.config.ts`)

Custom colors, spacing, and utilities are defined here.

#### Global Styles (`app/globals.css`)

CSS variables for theming:

```css
:root {
  --background: 0 0% 100%;
  --foreground: 240 10% 3.9%;
  --primary: 240 5.9% 10%;
  /* ... more variables */
}
```

#### Using Tailwind Classes

```tsx
<div className="flex items-center justify-between p-4 bg-white rounded-lg shadow-md">
  <h2 className="text-xl font-bold text-gray-900">Job Name</h2>
  <Button variant="outline" size="sm">Edit</Button>
</div>
```

#### Conditional Classes with clsx

```tsx
import { clsx } from 'clsx';

<div className={clsx(
  'p-4 rounded',
  isActive ? 'bg-green-100' : 'bg-gray-100',
  hasError && 'border-2 border-red-500'
)}>
  Content
</div>
```

### Dark Mode

Dark mode is configured but not yet implemented in UI. CSS variables are defined for both light and dark themes in `globals.css`.

**To enable dark mode:**

1. Add theme toggle component
2. Use `dark:` prefix in Tailwind classes
3. Toggle `dark` class on `<html>` element

---

## Troubleshooting

### Common Issues

#### 1. "Clerk is not configured"

**Cause:** Missing Clerk environment variables

**Solution:**
```bash
# Ensure .env.local has:
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx

# Restart dev server
pnpm dev
```

#### 2. "Cannot connect to backend API"

**Cause:** Incorrect API URL or CORS issues

**Solution:**
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Ensure backend API has CORS enabled for your frontend domain
- Check backend logs for request errors

#### 3. Build Fails with "Type error"

**Cause:** TypeScript type errors

**Solution:**
```bash
# Run type check to see all errors
npx tsc --noEmit

# Fix type errors in reported files
```

#### 4. "Module not found" Error

**Cause:** Missing dependencies or incorrect imports

**Solution:**
```bash
# Reinstall dependencies
rm -rf node_modules .next
pnpm install
```

#### 5. Styles Not Loading

**Cause:** Tailwind CSS or PostCSS configuration issue

**Solution:**
- Check `tailwind.config.ts` is correct
- Check `postcss.config.mjs` is correct
- Restart dev server
- Clear `.next` cache

### Debugging

#### Enable Verbose Logging

```bash
# Next.js debug mode
NODE_OPTIONS='--inspect' pnpm dev

# View console logs in browser DevTools
```

#### Check Network Requests

1. Open browser DevTools (F12)
2. Go to Network tab
3. Filter by "Fetch/XHR"
4. Check API requests and responses

---

## Performance Optimization (Phase 6 & 8)

### Planned Improvements

1. **Code Splitting** (automatic with Next.js)
2. **Image Optimization** (Next.js Image component)
3. **Data Fetching**
   - Implement React Query or SWR
   - Add optimistic UI updates
   - Client-side caching

4. **Real-Time Updates** (Phase 8)
   - WebSocket connection for job progress
   - Server-Sent Events (SSE)

5. **UI Performance**
   - Virtualize long job lists
   - Memoize expensive components
   - Lazy load modal components

---

## Testing (Phase 3)

### Coming Soon

Unit and integration tests using:
- **Jest** - Test runner
- **React Testing Library** - Component testing
- **Playwright** or **Cypress** - E2E testing

---

## Contributing

See [IMPLEMENTATION_PLAN.md](../../IMPLEMENTATION_PLAN.md) for development roadmap and current priorities.

---

## Support

- Backend API: See [backend/README.md](../../backend/README.md)
- Architecture: See [ARCHITECTURE.md](../../ARCHITECTURE.md)
- Roadmap: See [IMPLEMENTATION_PLAN.md](../../IMPLEMENTATION_PLAN.md)

---

**Last Updated:** January 8, 2026
