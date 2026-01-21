/**
 * Next.js Error Page
 * Global error boundary for the application
 */

'use client';

import { useEffect } from 'react';
import { ErrorFallback } from '@/components/ErrorFallback';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    // Log error to console
    console.error('Application error:', error);

    // TODO: Log to error reporting service (Sentry, LogRocket, etc.)
  }, [error]);

  return <ErrorFallback error={error} resetError={reset} fullPage />;
}
