# Component Library Documentation

This directory contains all React components for the SnowScrape application, organized by category.

## Directory Structure

```
components/
├── ui/                 # shadcn/ui base components (20+ components)
├── layout/             # Layout components (AppLayout, AppSidebar, AppTopNav)
├── providers/          # Provider components (QueryProvider, ToastProvider)
├── JobCard.tsx         # Job display card
├── JobModal.tsx        # Job creation/edit modal
├── StatCard.tsx        # Metric display card
├── EmptyState.tsx      # Empty state component
├── PageHeader.tsx      # Page header with breadcrumbs
├── StatusBadge.tsx     # Job status badge
├── ConfirmDialog.tsx   # Confirmation dialog
├── ErrorBoundary.tsx      # Error boundary wrapper
├── ErrorFallback.tsx      # Error fallback UI
├── LoadingSpinner.tsx     # Loading spinner
├── LoadingSkeleton.tsx    # Skeleton placeholders
├── NotificationCenter.tsx # Notification bell dropdown
├── OnboardingTour.tsx     # Interactive onboarding (3 components)
└── ...
```

## Component Categories

### 1. UI Components (`ui/`)

Base UI components from shadcn/ui, built on Radix UI primitives with Tailwind styling:

- **badge** - Status indicators and labels
- **button** - Interactive buttons with variants
- **card** - Container component for content
- **dialog** - Modal dialogs and overlays
- **dropdown-menu** - Dropdown menu component
- **form** - Form components with validation
- **input** - Text input fields
- **select** - Dropdown select component
- **tabs** - Tabbed interface component
- **toast** - Toast notification system
- **tooltip** - Hover tooltips
- ...and more

All UI components support:
- Dark mode
- Keyboard navigation
- ARIA accessibility
- TypeScript types

### 2. Layout Components (`layout/`)

#### `AppLayout`
Main application layout combining sidebar and top navigation.

```tsx
import { AppLayout } from '@/components/layout';

<AppLayout>
  {/* Your page content */}
</AppLayout>
```

**Features:**
- Responsive sidebar (collapsible on mobile)
- Top navigation with search and user menu
- Proper scroll handling

#### `AppSidebar`
Collapsible sidebar with navigation links, recent jobs, and quick actions.

**Props:**
- None (uses internal state)

#### `AppTopNav`
Top navigation bar with search, notifications, and user menu.

**Props:**
- `onMenuClick?: () => void` - Callback for mobile menu toggle

#### `MarketingLayout`
Layout for marketing/public pages with header and footer.

```tsx
import { MarketingLayout } from '@/components/layout';

<MarketingLayout>
  {/* Marketing page content */}
</MarketingLayout>
```

### 3. Feature Components

#### `JobCard`
Displays a single job with actions (view, pause/resume, download, delete).

```tsx
import { JobCard } from '@/components/JobCard';

<JobCard
  job={job}
  onClick={() => handleViewJob(job)}
  onPause={() => handlePause(job.job_id)}
  onResume={() => handleResume(job.job_id)}
  onDelete={() => handleDelete(job.job_id)}
  onDownload={(format) => handleDownload(job.job_id, format)}
  onPreview={() => handlePreview(job)}
/>
```

**Props:**
- `job: Job` - Job object
- `onClick: () => void` - Click handler for viewing details
- `onPause?: () => void` - Handler for pausing job
- `onResume?: () => void` - Handler for resuming job
- `onDelete: () => void` - Handler for deleting job
- `onDownload?: (format: string) => void` - Handler for downloading results
- `onPreview?: () => void` - Handler for previewing results

**Features:**
- Status badge with color coding
- Hover effects with accent color
- Dropdown menu for actions
- Delete confirmation dialog
- Export format selection (JSON, CSV, Excel, Parquet, SQL)

#### `StatCard`
Displays a metric with optional trend indicator.

```tsx
import { StatCard } from '@/components/StatCard';

<StatCard
  title="Total Jobs"
  value={42}
  icon={<BriefcaseIcon />}
  trend="up"
  change={12}
  changeLabel="vs last month"
/>
```

**Props:**
- `title: string` - Metric title
- `value: string | number` - Metric value
- `icon?: React.ReactNode` - Optional icon
- `trend?: 'up' | 'down' | 'neutral'` - Trend direction
- `change?: number` - Change amount
- `changeLabel?: string` - Change label (e.g., "vs last month")
- `className?: string` - Additional CSS classes

#### `EmptyState`
Displays an empty state with icon, message, and optional action.

```tsx
import { EmptyState } from '@/components/EmptyState';

<EmptyState
  icon={<BriefcaseIcon />}
  title="No jobs yet"
  description="Create your first scraping job to get started."
  action={{
    label: "Create Job",
    onClick: () => handleCreateJob()
  }}
/>
```

**Props:**
- `icon?: React.ReactNode` - Optional icon
- `title: string` - Main title
- `description: string` - Description text
- `action?: { label: string; onClick: () => void }` - Optional action button
- `className?: string` - Additional CSS classes

#### `PageHeader`
Page header with title, description, breadcrumbs, and actions.

```tsx
import { PageHeader } from '@/components/PageHeader';

<PageHeader
  title="Dashboard"
  description="Manage your scraping jobs"
  breadcrumbs={[
    { label: "Home", href: "/" },
    { label: "Dashboard", href: "/dashboard" }
  ]}
  actions={
    <Button onClick={handleCreate}>
      <Plus className="mr-2 h-4 w-4" />
      New Job
    </Button>
  }
/>
```

**Props:**
- `title: string` - Page title
- `description?: string` - Optional description
- `breadcrumbs?: Breadcrumb[]` - Optional breadcrumb navigation
- `actions?: React.ReactNode` - Optional action buttons
- `className?: string` - Additional CSS classes

#### `StatusBadge`
Specialized badge for displaying job status.

```tsx
import { StatusBadge } from '@/components/StatusBadge';

<StatusBadge status="running" size="md" showIcon />
```

**Props:**
- `status: 'running' | 'success' | 'failed' | 'paused' | 'scheduled'` - Job status
- `size?: 'sm' | 'md' | 'lg'` - Badge size
- `showIcon?: boolean` - Whether to show status icon
- `className?: string` - Additional CSS classes

**Status Colors:**
- `running` - Blue
- `success` - Green
- `failed` - Red
- `paused` - Orange
- `scheduled` - Gray

#### `ConfirmDialog`
Reusable confirmation dialog.

```tsx
import { ConfirmDialog } from '@/components/ConfirmDialog';

<ConfirmDialog
  open={isOpen}
  onOpenChange={setIsOpen}
  onConfirm={handleConfirm}
  title="Delete Job"
  description="Are you sure? This action cannot be undone."
  confirmLabel="Delete"
  variant="destructive"
  loading={isDeleting}
/>
```

**Props:**
- `open: boolean` - Dialog open state
- `onOpenChange: (open: boolean) => void` - Handler for open state change
- `onConfirm: () => void` - Confirm action handler
- `title: string` - Dialog title
- `description: string` - Dialog description
- `confirmLabel?: string` - Confirm button label (default: "Confirm")
- `cancelLabel?: string` - Cancel button label (default: "Cancel")
- `variant?: 'default' | 'destructive'` - Button variant
- `loading?: boolean` - Loading state for confirm button

### 4. Error Handling Components

#### `ErrorBoundary`
React error boundary to catch component errors.

```tsx
import { ErrorBoundary } from '@/components/ErrorBoundary';

<ErrorBoundary onError={(error, errorInfo) => logError(error)}>
  <YourComponent />
</ErrorBoundary>
```

**Props:**
- `children: React.ReactNode` - Child components
- `fallback?: React.ReactNode` - Optional custom fallback UI
- `onError?: (error: Error, errorInfo: React.ErrorInfo) => void` - Error handler

#### `ErrorFallback`
Error fallback UI displayed by ErrorBoundary.

```tsx
import { ErrorFallback } from '@/components/ErrorFallback';

<ErrorFallback
  error={error}
  resetError={() => handleReset()}
  fullPage
/>
```

**Props:**
- `error: Error | null` - Error object
- `resetError?: () => void` - Reset error handler
- `fullPage?: boolean` - Whether to use full page layout

### 5. Loading Components

#### `LoadingSpinner`
Animated loading spinner.

```tsx
import { LoadingSpinner, LoadingSpinnerFullPage } from '@/components/LoadingSpinner';

<LoadingSpinner size="lg" text="Loading..." />

// Or full page variant
<LoadingSpinnerFullPage text="Loading application..." />
```

**Props:**
- `size?: 'sm' | 'md' | 'lg' | 'xl'` - Spinner size
- `className?: string` - Additional CSS classes
- `text?: string` - Optional loading text

#### `LoadingSkeleton`
Skeleton placeholders for loading states.

```tsx
import {
  Skeleton,
  CardSkeleton,
  TableSkeleton,
  JobCardSkeleton,
  DashboardSkeleton
} from '@/components/LoadingSkeleton';

// Basic skeleton
<Skeleton className="h-4 w-full" />

// Card skeleton
<CardSkeleton />

// Table skeleton
<TableSkeleton count={5} />

// Job card skeleton
<JobCardSkeleton />

// Full dashboard skeleton
<DashboardSkeleton />
```

**Components:**
- `Skeleton` - Basic skeleton element
- `CardSkeleton` - Card loading placeholder
- `TableSkeleton` - Table loading placeholder
- `TableRowSkeleton` - Single table row placeholder
- `JobCardSkeleton` - Job card loading placeholder
- `DashboardSkeleton` - Full dashboard loading state

### 6. Notification Components

#### `NotificationCenter`
Bell icon dropdown with notification management.

```tsx
import { NotificationCenter } from '@/components/NotificationCenter';

// Typically integrated in AppTopNav
<NotificationCenter />
```

**Features:**
- Unread notification count badge (9+ for 10 or more)
- Dropdown panel with All/Unread tabs
- Notification items with:
  - Type icons (success, error, warning, info)
  - Title and message
  - Time ago (e.g., "5 minutes ago")
  - Link to related page
  - Mark as read button
  - Delete button
- Mark all as read action
- Link to full notifications page
- Settings link

**Notification Types:**
- `success` - Green checkmark (job completed, etc.)
- `error` - Red X (job failed, etc.)
- `warning` - Yellow alert (usage limits, etc.)
- `info` - Blue info (system updates, etc.)

**Notification Categories:**
- `job` - Job-related notifications
- `system` - System updates and announcements
- `billing` - Billing and usage notifications
- `security` - Security and account notifications

**Props:**
- None (manages its own state and fetches notifications)

**Usage:**
Already integrated into `AppTopNav`. Displays in the top navigation bar.

### 7. Onboarding Components

#### `OnboardingTour`
Interactive 4-step tutorial modal for new users.

```tsx
import { OnboardingTour } from '@/components/OnboardingTour';

// Typically placed at the end of the main layout
<OnboardingTour />
```

**Features:**
- Auto-triggers on first visit (checks localStorage)
- 4 steps with progress bar:
  1. Welcome to SnowScrape
  2. Start with Templates
  3. Visual Scraper Builder
  4. Monitor Performance
- Each step has:
  - Icon
  - Title and description
  - Optional action button (links to feature)
- Navigation: Skip Tutorial, Back, Next, Get Started
- Completion tracked in localStorage (`onboarding_completed`)

**Props:**
- None (manages its own state)

**Usage:**
```tsx
<OnboardingTour />
```

#### `QuickStartGuide`
Dismissible quick-start card for dashboard.

```tsx
import { QuickStartGuide } from '@/components/OnboardingTour';

<QuickStartGuide />
```

**Features:**
- 3 quick-start options:
  1. Use a Template
  2. Visual Builder
  3. Manual Setup
- Dismissible (X button)
- Persists dismissal in localStorage (`quickstart_dismissed`)
- Gradient accent border styling
- Click handlers navigate to respective pages

**Props:**
- None (manages its own state)

**Usage:**
Typically placed at the top of the dashboard after the `PageHeader`.

#### `JobSuccessCelebration`
Success modal for celebrating first job completion.

```tsx
import { JobSuccessCelebration } from '@/components/OnboardingTour';

<JobSuccessCelebration jobName="My First Job" />
```

**Features:**
- Animated checkmark with bounce effect
- Congratulations message with job name
- "What's next?" section with actions:
  - View Results
  - Create Another Job
- Close button

**Props:**
- `jobName: string` - Name of the completed job

**Usage:**
Trigger when a user's first job completes successfully:
```tsx
{showCelebration && (
  <JobSuccessCelebration jobName={completedJob.name} />
)}
```

### 8. Provider Components (`providers/`)

#### `QueryProvider`
React Query provider with DevTools.

```tsx
import { QueryProvider } from '@/components/providers/QueryProvider';

<QueryProvider>
  {children}
</QueryProvider>
```

Automatically included in root layout.

#### `ToastProvider`
Toast notification provider.

```tsx
import { ToastProvider } from '@/components/providers/ToastProvider';

<ToastProvider />
```

Automatically included in root layout.

## Design System Integration

All components follow the SnowScrape design system:

### Colors
- **Brand Primary**: `#0A2540` (Deep blue) - `bg-brand-primary`, `text-brand-primary`
- **Brand Accent**: `#00D9FF` (Cyan) - `bg-brand-accent`, `text-brand-accent`
- **Status Colors**: Available via `status-running`, `status-success`, etc.

### Typography
- **Headings**: Inter font family
- **Body**: System font stack
- **Code**: JetBrains Mono

### Spacing
- Consistent spacing scale (4px increments)
- Accessible via Tailwind: `p-4`, `m-6`, `gap-2`, etc.

### Accessibility
- All interactive elements have proper ARIA labels
- Keyboard navigation supported
- Focus states visible
- Color contrast meets WCAG AA standards

## Usage Guidelines

### Importing Components

```tsx
// UI components
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

// Layout components
import { AppLayout } from '@/components/layout';

// Feature components
import { JobCard } from '@/components/JobCard';
import { StatCard } from '@/components/StatCard';
```

### Styling Components

All components accept a `className` prop for custom styling:

```tsx
<StatCard
  title="Total Jobs"
  value={42}
  className="col-span-2"
/>
```

Use Tailwind utility classes for styling. Brand colors are available:

```tsx
<div className="bg-brand-primary text-brand-accent">
  {/* Content */}
</div>
```

### Dark Mode

All components automatically support dark mode via Tailwind's `dark:` variant:

```tsx
<div className="bg-white dark:bg-gray-800">
  <p className="text-gray-900 dark:text-gray-100">Text</p>
</div>
```

## Best Practices

1. **Use shadcn/ui components** as building blocks for consistency
2. **Follow the design system** for colors, spacing, and typography
3. **Add proper TypeScript types** for all component props
4. **Include accessibility features** (ARIA labels, keyboard navigation)
5. **Support dark mode** for all custom components
6. **Use loading states** (skeletons) for better UX
7. **Handle errors gracefully** with ErrorBoundary
8. **Keep components focused** - single responsibility principle

## Adding New Components

When adding a new component:

1. Create component file in appropriate directory
2. Add TypeScript interface for props
3. Include JSDoc comments
4. Add to this README with examples
5. Ensure dark mode support
6. Add accessibility features
7. Test keyboard navigation

Example component template:

```tsx
/**
 * MyComponent Description
 * Detailed description of what this component does
 */

'use client';

import { cn } from '@/lib/utils';

interface MyComponentProps {
  /** Prop description */
  title: string;
  /** Optional prop description */
  description?: string;
  /** Additional CSS classes */
  className?: string;
}

export function MyComponent({
  title,
  description,
  className,
}: MyComponentProps) {
  return (
    <div className={cn('base-classes', className)}>
      <h3>{title}</h3>
      {description && <p>{description}</p>}
    </div>
  );
}
```

## Resources

- [shadcn/ui Documentation](https://ui.shadcn.com/)
- [Radix UI Primitives](https://www.radix-ui.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [React Query](https://tanstack.com/query/latest)
