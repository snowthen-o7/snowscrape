/**
 * Error boundary for the dashboard section.
 * Catches errors in jobs, analytics, templates, etc.
 * without disrupting the sidebar navigation.
 */

'use client';

import { useEffect } from 'react';
import * as Sentry from '@sentry/nextjs';
import { ErrorFallback } from '@/components/ErrorFallback';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function DashboardError({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    Sentry.captureException(error, {
      tags: { boundary: 'dashboard' },
      extra: { digest: error.digest },
    });
  }, [error]);

  return <ErrorFallback error={error} resetError={reset} />;
}
