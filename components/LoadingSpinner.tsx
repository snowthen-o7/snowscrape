/**
 * Loading Spinner Component
 * Displays an animated spinner for loading states
 */

'use client';

import { Loader2Icon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  text?: string;
}

const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-8 w-8',
  lg: 'h-12 w-12',
  xl: 'h-16 w-16',
};

export function LoadingSpinner({
  size = 'md',
  className,
  text,
}: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <Loader2Icon
        className={cn(
          'animate-spin text-brand-primary dark:text-brand-accent',
          sizeClasses[size],
          className
        )}
      />
      {text && (
        <p className="text-sm text-muted-foreground">{text}</p>
      )}
    </div>
  );
}

/**
 * Full page loading spinner
 */
export function LoadingSpinnerFullPage({
  text = 'Loading...',
}: {
  text?: string;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <LoadingSpinner size="xl" text={text} />
    </div>
  );
}
