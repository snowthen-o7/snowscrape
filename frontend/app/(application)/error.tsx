/**
 * Error boundary for the application dashboard section.
 * Catches errors in dashboard, webhooks, and other protected routes
 * without taking down the entire app.
 */

'use client';

import { useEffect } from 'react';
import * as Sentry from '@sentry/nextjs';
import { ErrorFallback } from '@/components/ErrorFallback';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ApplicationError({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    Sentry.captureException(error, {
      tags: { boundary: 'application' },
      extra: { digest: error.digest },
    });
  }, [error]);

  return <ErrorFallback error={error} resetError={reset} />;
}
