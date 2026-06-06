/**
 * Google OAuth Callback Page
 * Receives ?code=...&state=... from Google, completes OAuth via backend, redirects to /integrations.
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { AppLayout } from '@/components/layout';
import { PageHeader, Card, CardContent } from '@snowforge/ui';
import { useCompleteGoogleOAuth } from '@/lib/hooks/useGoogleAccount';

export default function GoogleCallbackPage() {
  const router = useRouter();
  const params = useSearchParams();
  const complete = useCompleteGoogleOAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = params.get('code');
    const state = params.get('state');
    const errParam = params.get('error');

    if (errParam) {
      setError(errParam);
      return;
    }
    if (!code || !state) {
      setError('Missing code or state parameter');
      return;
    }
    const expected = sessionStorage.getItem('google_oauth_state');
    if (expected !== state) {
      setError('State mismatch — possible CSRF. Try connecting again.');
      return;
    }
    sessionStorage.removeItem('google_oauth_state');

    complete.mutate(
      { code, state },
      {
        onSuccess: () => router.replace('/dashboard/integrations'),
        onError: (e: unknown) =>
          setError(e instanceof Error ? e.message : 'Connection failed'),
      },
    );
  }, [params, router]);

  if (error) {
    return (
      <AppLayout>
        <div className="space-y-6 p-6">
          <PageHeader
            title="Connection failed"
            description="Could not complete Google OAuth."
          />
          <Card>
            <CardContent className="p-6 space-y-4">
              <p className="text-destructive">{error}</p>
              <a
                className="text-primary underline"
                href="/dashboard/integrations"
              >
                Back to Integrations
              </a>
            </CardContent>
          </Card>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        <PageHeader
          title="Connecting…"
          description="Finishing your Google account connection."
        />
        <Card>
          <CardContent className="p-6 text-muted-foreground">
            One moment…
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
