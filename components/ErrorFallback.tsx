/**
 * Error Fallback Component
 * Displayed when an error is caught by ErrorBoundary
 */

'use client';

import { AlertTriangleIcon, RefreshCwIcon, HomeIcon } from 'lucide-react';
import {
  Button,
  Alert,
  AlertDescription,
  AlertTitle,
  Card,
} from '@snowforge/ui';

interface ErrorFallbackProps {
  error: Error | null;
  resetError?: () => void;
  fullPage?: boolean;
}

export function ErrorFallback({
  error,
  resetError,
  fullPage = false,
}: ErrorFallbackProps) {
  const handleGoHome = () => {
    window.location.href = '/dashboard';
  };

  const handleRefresh = () => {
    if (resetError) {
      resetError();
    } else {
      window.location.reload();
    }
  };

  const content = (
    <div className="flex flex-col items-center justify-center space-y-4">
      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-destructive/10">
        <AlertTriangleIcon className="h-10 w-10 text-destructive" />
      </div>

      <div className="text-center">
        <h2 className="text-2xl font-bold text-foreground">
          Something went wrong
        </h2>
        <p className="mt-2 text-muted-foreground">
          We encountered an unexpected error. Please try refreshing the page.
        </p>
      </div>

      {error && process.env.NODE_ENV === 'development' && (
        <Alert variant="destructive" className="max-w-2xl">
          <AlertTriangleIcon className="h-4 w-4" />
          <AlertTitle>Error Details (Development Only)</AlertTitle>
          <AlertDescription className="mt-2">
            <pre className="overflow-x-auto text-xs">
              {error.message}
              {'\n\n'}
              {error.stack}
            </pre>
          </AlertDescription>
        </Alert>
      )}

      <div className="flex gap-3">
        <Button onClick={handleRefresh} variant="default">
          <RefreshCwIcon className="mr-2 h-4 w-4" />
          Try Again
        </Button>
        <Button onClick={handleGoHome} variant="outline">
          <HomeIcon className="mr-2 h-4 w-4" />
          Go to Dashboard
        </Button>
      </div>
    </div>
  );

  if (fullPage) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        {content}
      </div>
    );
  }

  return (
    <Card className="p-8">
      {content}
    </Card>
  );
}
