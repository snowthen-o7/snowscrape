/**
 * Loading Skeleton Component
 * Displays skeleton placeholders during content loading
 */

'use client';

import { cn } from '@snowforge/ui';

interface LoadingSkeletonProps {
  className?: string;
  count?: number;
}

/**
 * Basic skeleton element
 */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-muted',
        className
      )}
    />
  );
}

/**
 * Card skeleton loader
 */
export function CardSkeleton({ className }: LoadingSkeletonProps) {
  return (
    <div className={cn('rounded-lg border bg-card p-6', className)}>
      <Skeleton className="mb-4 h-6 w-2/3" />
      <Skeleton className="mb-2 h-4 w-full" />
      <Skeleton className="mb-2 h-4 w-5/6" />
      <Skeleton className="h-4 w-4/6" />
      <div className="mt-4 flex gap-2">
        <Skeleton className="h-8 w-20" />
        <Skeleton className="h-8 w-20" />
      </div>
    </div>
  );
}

/**
 * Table row skeleton loader
 */
export function TableRowSkeleton({ className }: LoadingSkeletonProps) {
  return (
    <tr className={cn('border-b', className)}>
      <td className="p-4">
        <Skeleton className="h-4 w-full" />
      </td>
      <td className="p-4">
        <Skeleton className="h-4 w-full" />
      </td>
      <td className="p-4">
        <Skeleton className="h-4 w-full" />
      </td>
      <td className="p-4">
        <Skeleton className="h-4 w-20" />
      </td>
    </tr>
  );
}

/**
 * Table skeleton loader
 */
export function TableSkeleton({
  className,
  count = 5,
}: LoadingSkeletonProps) {
  return (
    <div className={cn('overflow-hidden rounded-lg border', className)}>
      <table className="w-full">
        <thead className="bg-muted/50">
          <tr>
            <th className="p-4 text-left">
              <Skeleton className="h-4 w-24" />
            </th>
            <th className="p-4 text-left">
              <Skeleton className="h-4 w-24" />
            </th>
            <th className="p-4 text-left">
              <Skeleton className="h-4 w-24" />
            </th>
            <th className="p-4 text-left">
              <Skeleton className="h-4 w-16" />
            </th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: count }).map((_, i) => (
            <TableRowSkeleton key={i} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Job card skeleton loader
 */
export function JobCardSkeleton({ className }: LoadingSkeletonProps) {
  return (
    <div
      className={cn(
        'rounded-lg border bg-card p-6 shadow-sm',
        className
      )}
    >
      <div className="mb-4 flex items-start justify-between">
        <div className="flex-1">
          <Skeleton className="mb-2 h-6 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
        </div>
        <Skeleton className="h-6 w-20" />
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-4 w-40" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-4 w-28" />
        </div>
      </div>

      <div className="mt-4 flex gap-2 border-t pt-4">
        <Skeleton className="h-9 w-24" />
        <Skeleton className="h-9 w-24" />
        <Skeleton className="ml-auto h-9 w-9" />
      </div>
    </div>
  );
}

/**
 * Dashboard skeleton loader
 */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Skeleton className="mb-2 h-8 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-10 w-32" />
      </div>

      {/* Stats cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border bg-card p-6">
            <Skeleton className="mb-2 h-4 w-24" />
            <Skeleton className="mb-1 h-8 w-20" />
            <Skeleton className="h-3 w-16" />
          </div>
        ))}
      </div>

      {/* Job cards */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <JobCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}
